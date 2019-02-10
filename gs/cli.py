#!/usr/bin/env python

import os, sys, json, textwrap, logging, fnmatch, mimetypes, datetime, time, base64, hashlib, concurrent.futures
from argparse import Namespace

import click, tweak, requests
from dateutil.parser import parse as dateutil_parse

from . import GSClient, GSUploadClient, GSBatchClient, logger
from .util import Timestamp, CRC32C, get_file_size, format_http_errors, batches
from .util.compat import makedirs, cpu_count
from .util.printing import page_output, tabulate, GREEN, BLUE, BOLD, format_number, get_progressbar
from .version import __version__

@click.group()
@click.version_option(version=__version__)
def cli():
    """gs is a minimalistic CLI for Google Cloud Storage."""
    logging.basicConfig(level=logging.INFO)

@click.command()
def configure():
    """Set gs config options, including the API key."""
    msg = ("Please open " + BOLD("https://console.cloud.google.com/iam-admin/serviceaccounts") + ", create a service "
           "account and download its private key. The service account should have a role with Google Storage access. "
           "Drag & drop the key file into this terminal window, or paste the file location or JSON contents below.")
    print("\n".join(textwrap.wrap(msg, 120)))
    prompt_msg = u"Service account key file path or contents"
    buf, filename = "", None
    while True:
        line = click.prompt(prompt_msg).strip()
        if line == "":
            if buf == "":
                continue
            break
        if buf == "" and not line.startswith("{"):
            filename = line
            break
        buf += line
        if line.endswith("}"):
            break
        prompt_msg = u""
    if filename:
        with open(os.path.expanduser(filename)) as fh:
            key = json.load(fh)
    else:
        key = json.loads(buf)
    client.config.service_credentials = key
    client.config.save()
    print("Key configuration saved.")

cli.add_command(configure)

def parse_bucket_and_prefix(path, require_gs_uri=True):
    if require_gs_uri:
        assert path.startswith("gs://")
    if path.startswith("gs://"):
        path = path[len("gs://"):]
    if "/" in path:
        bucket, prefix = path.split("/", 1)
    else:
        bucket, prefix = path, ""
    return bucket, prefix

@click.command()
@click.argument('path', required=False)
@click.option('--max-results', type=int, help="Limit the listing to this many results from the top.")
@click.option("--width", type=int, default=42, help="Limit table columns to this width.")
@click.option("--json", is_flag=True, help="Print output as JSON instead of tabular format.")
@format_http_errors
def ls(path, max_results=None, width=None, json=False):
    """List buckets or objects in a bucket/prefix."""
    if path is None:
        res = client.get("b", params=dict(project=client.get_project()))
        columns = ["name", "timeCreated", "updated", "location", "storageClass"]
        page_output(tabulate(res.get("items", []), args=Namespace(columns=columns, max_col_width=width, json=json)))
    else:
        bucket, prefix = parse_bucket_and_prefix(path, require_gs_uri=False)
        params = dict(delimiter="/")
        prefix = prefix.rstrip("*")
        if prefix:
            params["prefix"] = prefix
        if max_results:
            params["maxResults"] = max_results
        columns = ["name", "size", "timeCreated", "updated", "contentType", "storageClass"]
        items = client.list("b/{}/o".format(bucket), params=params)
        page_output(tabulate(items, args=Namespace(columns=columns, max_col_width=width, json=json)))

cli.add_command(ls)

def read_file_chunks(filename, hasher, chunk_size=1024 * 1024, progressbar=None, start_pos=0):
    if filename == "-":
        filename = "/dev/stdin"
    with open(filename, "rb") as fh:
        if start_pos > 0:
            while True:
                chunk = fh.read(min(chunk_size, max(start_pos - fh.tell(), 0)))
                if len(chunk) == 0:
                    break
                hasher.update(chunk)
        chunk = fh.read(chunk_size)
        yield chunk
        hasher.update(chunk)
        chunk = fh.read(chunk_size)
        if len(chunk) > 0:
            file_size = get_file_size(filename)
            if progressbar is None:
                progressbar = get_progressbar(length=file_size)
            with progressbar as bar:
                bar.update(chunk_size + start_pos)
                while True:
                    bar.update(chunk_size)
                    yield chunk
                    hasher.update(chunk)
                    chunk = fh.read(chunk_size)
                    if len(chunk) == 0:
                        break

def download_one_file(bucket, key, dest_filename, chunk_size=1024 * 1024, tmp_suffix=".gsdownload"):
    api_args = dict(bucket=bucket, key=key, dest_filename=dest_filename)
    staging_filename = "/dev/stdout" if dest_filename == "-" else dest_filename + tmp_suffix
    hasher, checksums, req_headers, progressbar, resume_pos = None, None, {}, None, 0
    escaped_args = {k: requests.compat.quote(v, safe="") for k, v in api_args.items()}
    if os.path.exists(staging_filename) and get_file_size(staging_filename) > chunk_size:
        logger.info("Checking partial download of %s", dest_filename)
        res = client.get("b/{bucket}/o/{key}".format(**escaped_args))
        checksums = {"md5": res.get("md5Hash"), "crc32c": res["crc32c"]}
        size = int(res["size"])
        progressbar = get_progressbar(length=size, fill_char=">", file=sys.stderr)
        hasher = hashlib.md5() if checksums.get("md5") else CRC32C()
        for chunk in read_file_chunks(staging_filename, hasher, progressbar=progressbar):
            resume_pos += len(chunk)
        req_headers.update(Range="bytes={}-{}".format(resume_pos, resume_pos + size))
        logger.info("Resuming download from %s", format_number(resume_pos))
    with open(staging_filename, "ab" if checksums else "wb") as fh:
        res = client.get("b/{bucket}/o/{key}".format(**escaped_args),
                         params=dict(alt="media"),
                         headers=req_headers,
                         stream=True)
        if checksums is None:
            checksums = requests.utils.parse_dict_header(res.headers["X-Goog-Hash"])
            size = int(res.headers["Content-Length"])
            hasher = hashlib.md5() if checksums.get("md5") else CRC32C()
        logger.info("Copying gs://{bucket}/{key} to {dest_filename} ({size})".format(size=format_number(size),
                                                                                     **api_args))
        chunk = res.raw.read(chunk_size)
        fh.write(chunk)
        hasher.update(chunk)
        chunk = res.raw.read(chunk_size)
        if len(chunk) > 0:
            if progressbar is None:
                progressbar = get_progressbar(length=size, file=sys.stderr)
            else:
                progressbar.fill_char = "#"
            with progressbar as bar:
                bar.update(len(chunk))
                while True:
                    bar.update(len(chunk))
                    fh.write(chunk)
                    hasher.update(chunk)
                    chunk = res.raw.read(chunk_size)
                    if len(chunk) == 0:
                        break
    assert hasher.digest() == base64.b64decode(checksums.get("md5") or checksums["crc32c"])
    if staging_filename.endswith(tmp_suffix):
        os.rename(staging_filename, dest_filename)
        os.utime(dest_filename, (time.time(), int(res.headers["X-Goog-Generation"]) // 1000000))

def upload_one_file(path, dest_bucket, dest_key, chunk_size=1024 * 1024, content_type=None, content_encoding=None,
                    content_disposition=None, content_language=None, cache_control=None, metadata=None):
    logger.info("Copying {path} to gs://{bucket}/{key}".format(path=path, bucket=dest_bucket, key=dest_key))
    headers, upload_id, resume_pos = {}, None, 0
    if content_type is None and content_encoding is None:
        content_type, content_encoding = mimetypes.guess_type(path)
    if content_type is not None:
        headers["Content-Type"] = content_type
    hasher = hashlib.md5()
    file_size = get_file_size(path)
    if file_size > chunk_size:
        cache_key_data = path + str(file_size) + dest_bucket + dest_key
        cache_key = base64.b64encode(hashlib.md5(cache_key_data.encode()).digest()).decode()
        client.config.setdefault("uploads", {})
        if cache_key in client.config.uploads:
            upload_id = client.config.uploads[cache_key]["u"]
            try:
                res = upload_client.put("b/{bucket}/o".format(bucket=requests.compat.quote(dest_bucket)),
                                        headers={"Content-Length": "0", "Content-Range": "bytes */" + str(file_size)},
                                        params=dict(uploadType="resumable", upload_id=upload_id),
                                        stream=True)
                assert res.status_code == 308
                start, end = requests.utils.parse_dict_header(res.headers["Range"])["bytes"].split("-")
                assert start == "0"
                resume_pos = int(end) + 1
                headers["Content-Range"] = "bytes {}-{}/{}".format(resume_pos, file_size - 1, file_size)
                logger.info("Resuming upload from %s", format_number(resume_pos))
            except (requests.exceptions.HTTPError, AssertionError):
                upload_id = None
        if upload_id is None:
            res = upload_client.post("b/{bucket}/o".format(bucket=requests.compat.quote(dest_bucket)),
                                     params=dict(uploadType="resumable"),
                                     json=dict(name=dest_key),
                                     stream=True)
            upload_id = res.headers["X-GUploader-UploadID"]
            # TODO: admit more than one entry into the upload id cache
            # if len(client.config.uploads) > cache_size:
            #     sorted_uids = sorted(client.config.uploads, key=lambda i: client.config.uploads[i]["t"])
            #     client.config.uploads = {k: client.config.uploads[k] for k in sorted_uids[:cache_size]}
            client.config.uploads = {}
            client.config.uploads[cache_key] = dict(u=upload_id, t=int(time.time()))
            try:
                client.config.save()
            except Exception as e:
                logger.warn("Error saving upload state to local config: %s. Upload is not resumable.", e)
        params = dict(uploadType="resumable", upload_id=upload_id)
    else:
        params = dict(uploadType="media", name=dest_key)
    res = upload_client.post("b/{bucket}/o".format(bucket=requests.compat.quote(dest_bucket)),
                             params=params,
                             headers=headers,
                             data=read_file_chunks(path, hasher, chunk_size=chunk_size, start_pos=resume_pos))
    if hasher.digest() != base64.b64decode(res["md5Hash"]):
        client.delete("b/{bucket}/o/{key}".format(bucket=requests.compat.quote(dest_bucket),
                                                  key=requests.compat.quote(dest_key, safe="")))
        raise Exception("Upload checksum mismatch in {}".format(dest_key))
    if metadata or content_disposition or content_encoding or content_language or cache_control:
        client.patch("b/{bucket}/o/{key}".format(bucket=requests.compat.quote(dest_bucket),
                                                 key=requests.compat.quote(dest_key, safe="")),
                     json=dict(metadata=dict(metadata), contentDisposition=content_disposition,
                               contentEncoding=content_encoding, contentLanguage=content_language,
                               cacheControl=cache_control))

@click.command()
@click.argument('paths', nargs=-1, required=True)
@click.option('--content-type', help="Set the content type to this value when uploading (guessed by default).")
@click.option('--content-encoding', help="Set the Content-Encoding header to this value (guessed by default).")
@click.option('--content-language', help="Set the Content-Language header to this value.")
@click.option('--content-disposition', help="Set the Content-Disposition header to this value.")
@click.option('--cache-control', help="Set the Cache-Control header to this value.")
@click.option('--metadata', multiple=True, metavar="KEY=VALUE", type=lambda x: x.split("=", 1),
              help="Set metadata on destination object(s) (can be specified multiple times).")
@format_http_errors
def cp(paths, **upload_metadata_kwargs):
    """
    Copy files to, from, or between buckets. Examples:

      gs cp * gs://my-bucket/my-prefix/

      gs cp gs://my-bucket/x .

      gs cp gs://my-bucket/foo gs://my-other-bucket/bar

    Use "-" to work with standard input or standard output:

      cat my-file | gs cp - gs://my-bucket/my-file

      gs cp gs://my-bucket/my-file.json - | jq .
    """
    assert len(paths) >= 2
    paths = [os.path.expanduser(p) for p in paths]
    api_method_template = "b/{source_bucket}/o/{source_key}/copyTo/b/{dest_bucket}/o/{dest_key}"
    if all(p.startswith("gs://") for p in paths):
        for path in paths[:-1]:
            source_bucket, source_key = parse_bucket_and_prefix(path)
            dest_bucket, dest_prefix = parse_bucket_and_prefix(paths[-1])
            dest_key = dest_prefix
            # TODO: check if dest_prefix is a prefix on the remote
            if dest_prefix.endswith("/") or len(paths) > 2:
                dest_key = os.path.join(dest_prefix, os.path.basename(source_key))
            api_args = dict(source_bucket=source_bucket,
                            source_key=source_key,
                            dest_bucket=dest_bucket,
                            dest_key=dest_key)
            logger.info("Copying gs://{source_bucket}/{source_key} to gs://{dest_bucket}/{dest_key}".format(**api_args))
            escaped_args = {k: requests.compat.quote(v, safe="") for k, v in api_args.items()}
            client.post(api_method_template.format(**escaped_args))
    elif all(p.startswith("gs://") for p in paths[:-1]) and not paths[-1].startswith("gs://"):
        # TODO: support remote wildcards
        for path in paths[:-1]:
            source_bucket, source_key = parse_bucket_and_prefix(path)
            dest_filename = paths[-1]
            if os.path.isdir(dest_filename) or len(paths) > 2:
                dest_filename = os.path.join(dest_filename, os.path.basename(source_key))
            download_one_file(bucket=source_bucket, key=source_key, dest_filename=dest_filename)
    elif paths[-1].startswith("gs://") and not any(p.startswith("gs://") for p in paths[0:-1]):
        for path in paths[:-1]:
            dest_bucket, dest_prefix = parse_bucket_and_prefix(paths[-1])
            dest_key = dest_prefix
            # TODO: check if dest_prefix is a prefix on the remote
            if dest_prefix == "" or dest_prefix.endswith("/") or len(paths) > 2:
                dest_key = os.path.join(dest_prefix, os.path.basename(path))
            upload_one_file(path, dest_bucket, dest_key, **upload_metadata_kwargs)
    else:
        raise click.BadParameter("paths")

cli.add_command(cp)

@click.command()
@click.argument('paths', nargs=-1, required=True)
@format_http_errors
def mv(paths):
    """Move files to, from, or between buckets."""
    cp.main(paths, standalone_mode=False)
    rm(paths[:-1])

cli.add_command(mv)

def batch_delete_prefix(bucket, prefix, max_workers, require_separator="/"):
    if prefix and require_separator and not prefix.endswith(require_separator):
        prefix += require_separator
    list_params = dict(prefix=prefix) if prefix else dict()
    items = client.list("b/{}/o".format(bucket), params=list_params)
    futures, total = [], 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as threadpool:
        for batch in batches(items, batch_size=100):
            logger.info("Deleting batch of %d objects in gs://%s/%s", len(batch), bucket, prefix)
            futures.append(threadpool.submit(batch_client.post_batch, [
                requests.Request(method="DELETE",
                                 url="b/{bucket}/o/{key}".format(bucket=requests.compat.quote(bucket),
                                                                 key=requests.compat.quote(obj_desc["name"], safe="")))
                for obj_desc in batch
            ]))
        for future in futures:
            total += len(future.result())
    return total

@click.command()
@click.argument('paths', nargs=-1, required=True)
@click.option("--recursive", is_flag=True,
              help="If a given path is a directory (prefix), delete all objects sharing that prefix.")
@click.option("--max-workers", type=int, default=cpu_count(),
              help="Limit batch delete concurrency to this many threads (default: number of CPU cores detected)")
@format_http_errors
def rm(paths, recursive=False, max_workers=None):
    """Delete objects (files) from buckets."""
    if not all(p.startswith("gs://") for p in paths):
        raise click.BadParameter("All paths must start with gs://")
    num_deleted = 0
    for path in paths:
        bucket, prefix = parse_bucket_and_prefix(path)
        print("Deleting gs://{bucket}/{key}".format(bucket=bucket, key=prefix))
        try:
            client.delete("b/{bucket}/o/{key}".format(bucket=requests.compat.quote(bucket),
                                                      key=requests.compat.quote(prefix, safe="")))
            num_deleted += 1
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == requests.codes.not_found:
                if recursive:
                    num_deleted += batch_delete_prefix(bucket, prefix, max_workers=max_workers)
                else:
                    msg = '{}. To recursively delete directories (prefixes), use "gs rm --recursive PATH".'
                    raise Exception(msg.format(e.response.json()["error"]["message"]))
            else:
                raise
    print("Done. {} files deleted.".format(num_deleted))
cli.add_command(rm)

@click.command()
@click.argument('paths', nargs=2, required=True)
@click.option("--max-workers", type=int, default=cpu_count(),
              help="Limit upload/download concurrency to this many threads (default: number of CPU cores detected)")
@format_http_errors
def sync(paths, max_workers=None):
    """Sync a directory of files with bucket/prefix."""
    src, dest = [os.path.expanduser(p) for p in paths]
    futures = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as threadpool:
        if src.startswith("gs://") and not dest.startswith("gs://"):
            bucket, prefix = parse_bucket_and_prefix(src)
            prefix = prefix.rstrip("*")
            list_params = dict(prefix=prefix) if prefix else dict()
            items = client.list("b/{}/o".format(bucket), params=list_params)
            for remote_object in items:
                try:
                    local_path = os.path.join(dest, remote_object["name"])
                    local_size = get_file_size(local_path)
                    local_mtime = datetime.datetime.utcfromtimestamp(os.path.getmtime(local_path))
                    remote_mtime = dateutil_parse(remote_object["updated"]).replace(tzinfo=None, microsecond=0)
                    if local_size == int(remote_object["size"]) and remote_mtime <= local_mtime:
                        logger.debug("sync:%s:%s: size/mtime match, skipping", src, local_path)
                        continue
                except OSError:
                    pass
                makedirs(os.path.dirname(local_path), exist_ok=True)
                futures.append(threadpool.submit(download_one_file, bucket, remote_object["name"], local_path))
        elif dest.startswith("gs://") and not src.startswith("gs://"):
            bucket, prefix = parse_bucket_and_prefix(dest)
            list_params = dict(prefix=prefix) if prefix else dict()
            remote_objects = {i["name"]: i for i in client.list("b/{}/o".format(bucket), params=list_params)}
            for root, dirs, files in os.walk(src):
                for filename in files:
                    local_path = os.path.join(root, filename)
                    local_size = get_file_size(local_path)
                    local_mtime = datetime.datetime.utcfromtimestamp(os.path.getmtime(local_path))
                    remote_path = os.path.join(prefix, os.path.relpath(root, src).lstrip("./"), filename)
                    try:
                        remote_object = remote_objects[remote_path]
                        remote_mtime = dateutil_parse(remote_object["updated"]).replace(tzinfo=None, microsecond=0)
                        if local_size == int(remote_object["size"]) and remote_mtime >= local_mtime:
                            logger.debug("sync:%s:%s: size/mtime match, skipping", local_path, dest)
                            continue
                    except KeyError:
                        pass
                    futures.append(threadpool.submit(upload_one_file, local_path, bucket, remote_path))
        else:
            raise click.BadParameter("Expected a local directory and a gs:// URL or vice versa")

        for future in futures:
            future.result()

cli.add_command(sync)

@click.command()
@click.argument('path', required=True)
@click.option('--expires-in', type=Timestamp, default="1h",
              help=('Time when or until the presigned URL expires. Examples: 60s, 5m, 1h, 2d, 3w, 2020-01-01, 15:20, '
                    '1535651591 (seconds since epoch). Default 1h.'))
def presign(path, expires_in=Timestamp("1h")):
    """Get a pre-signed URL for accessing an object."""
    bucket, key = parse_bucket_and_prefix(path)
    print(client.get_presigned_url(bucket, key, expires_at=expires_in.timestamp()))

cli.add_command(presign)

@click.command()
@click.argument('bucket_name')
@click.option('--location')
@click.option('--storage-class', type=click.Choice(choices=["STANDARD", "MULTI_REGIONAL", "NEARLINE", "COLDLINE",
                                                            "DURABLE_REDUCED_AVAILABILITY"]))
@format_http_errors
def mb(bucket_name, storage_class=None, location=None):
    """Create a new Google Storage bucket."""
    logger.info("Creating new Google Storage bucket {}".format(bucket_name))
    api_params = dict(name=bucket_name)
    if location:
        api_params["location"] = location
    if storage_class:
        api_params["storageClass"] = storage_class
    res = client.post("b", params=dict(project=client.get_project()), json=api_params)
    print(json.dumps(res, indent=4))

cli.add_command(mb)

@click.command()
@click.argument('bucket_name')
@format_http_errors
def rb(bucket_name):
    """Permanently delete an empty bucket."""
    print("Deleting Google Storage bucket {}".format(bucket_name))
    client.delete("b/{}".format(requests.compat.quote(bucket_name)))

cli.add_command(rb)

@click.command()
@click.argument('method')
@click.argument('gs_url')
@click.argument('args', nargs=-1)
def api(method, gs_url, args):
    """
    Use httpie to perform a raw HTTP API request.

    Example:

      gs api head gs://my-bucket/my-blob
    """
    bucket, prefix = parse_bucket_and_prefix(gs_url, require_gs_uri=False)
    path = "b/{bucket}".format(bucket=requests.compat.quote(bucket))
    args = list(args) + ["Authorization: Bearer " + client.get_oauth2_token(), "--check-status"]
    if prefix:
        path += "/o/{key}".format(key=requests.compat.quote(prefix, safe=""))
    try:
        os.execvp("http", ["http", method, client.base_url + path] + args)
    except EnvironmentError:
        exit("Error launching http. Please ensure httpie is installed (pip install httpie).")

cli.add_command(api)

client = GSClient()
upload_client = GSUploadClient(config=client.config)
batch_client = GSBatchClient(config=client.config)
