import os, sys, json, datetime, logging, base64

from gs.util.exceptions import NoServiceCredentials

import requests

logger = logging.getLogger(__name__)

class GSClient:
    base_url = "https://www.googleapis.com/storage/v1/"
    presigned_url_base = "https://storage.googleapis.com/"
    scope = "https://www.googleapis.com/auth/cloud-platform"
    instance_metadata_url = "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token"
    suppress_paging_warning = False

    def __init__(self, config, **session_kwargs):
        self.config = config
        self._service_jwt = None
        self._oauth2_token = None
        self._session = None
        self._session_kwargs = session_kwargs

    def get_session(self):
        if self._session is None:
            self._session = requests.Session(**self._session_kwargs)
            self._session.headers.update({"Authorization": "Bearer " + self.get_oauth2_token(),
                                          "User-Agent": self.__class__.__name__})
        return self._session

    def get_oauth2_token(self):
        # TODO: invalidate and refetch before expiration
        if self._oauth2_token is None:
            try:
                service_jwt = self.get_service_jwt()
                params = dict(grant_type="urn:ietf:params:oauth:grant-type:jwt-bearer", assertion=service_jwt)
                res = self.get_session().post("https://www.googleapis.com/oauth2/v4/token", data=params)
            except NoServiceCredentials:
                try:
                    res = requests.get(self.instance_metadata_url, headers={"Metadata-Flavor": "Google"})
                except Exception:
                    sys.exit('API credentials not configured. Please run "gs configure" '
                             'or set GOOGLE_APPLICATION_CREDENTIALS.')
            res.raise_for_status()
            self._oauth2_token = res.json()["access_token"]
        return self._oauth2_token

    def get_service_jwt(self):
        if self._service_jwt is None:
            if "service_credentials" not in self.config:
                if "GOOGLE_APPLICATION_CREDENTIALS" in os.environ:
                    logging.info("Using GOOGLE_APPLICATION_CREDENTIALS file %s",
                                 os.environ["GOOGLE_APPLICATION_CREDENTIALS"])
                    with open(os.environ["GOOGLE_APPLICATION_CREDENTIALS"]) as fh:
                        self.config.service_credentials = json.load(fh)
                else:
                    raise NoServiceCredentials()

            payload = {
                'iss': self.config.service_credentials["client_email"],
                'sub': self.config.service_credentials["client_email"],
                'scope': self.scope,
                'aud': "https://www.googleapis.com/oauth2/v4/token",
                'iat': datetime.datetime.utcnow(),
                'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=60)
            }
            additional_headers = {'kid': self.config.service_credentials["private_key_id"]}
            import jwt
            self._service_jwt = jwt.encode(payload,
                                           self.config.service_credentials["private_key"],
                                           headers=additional_headers,
                                           algorithm='RS256').decode()
        return self._service_jwt

    def request(self, method, resource, **kwargs):
        res = self.get_session().request(method=method, url=self.base_url + resource, **kwargs)
        res.raise_for_status()
        return res if kwargs.get("stream") is True or method == "delete" else res.json()

    def get(self, resource, **kwargs):
        return self.request(method="get", resource=resource, **kwargs)

    def post(self, resource, **kwargs):
        return self.request(method="post", resource=resource, **kwargs)

    def patch(self, resource, **kwargs):
        return self.request(method="patch", resource=resource, **kwargs)

    def put(self, resource, **kwargs):
        return self.request(method="put", resource=resource, **kwargs)

    def delete(self, resource, **kwargs):
        return self.request(method="delete", resource=resource, **kwargs)

    def get_project(self):
        if "GOOGLE_CLOUD_PROJECT" in os.environ:
            return os.environ["GOOGLE_CLOUD_PROJECT"]
        elif "service_credentials" in self.config:
            return self.config.service_credentials["project_id"]

    def list(self, resource, **kwargs):
        while True:
            page = self.request(method="get", resource=resource, **kwargs)
            items = [dict(name=i) for i in page.get("prefixes", [])] + page.get("items", [])
            for item in items:
                yield item
                if "maxResults" in kwargs["params"]:
                    kwargs["params"]["maxResults"] -= 1
                    if kwargs["params"]["maxResults"] == 0:
                        return
            if "nextPageToken" in page:
                if not self.suppress_paging_warning:
                    logger.warn("Large number of results returned. Listing may take a while. "
                                "You can limit the object count using the --max-results option.")
                    self.suppress_paging_warning = True
                kwargs["params"]["pageToken"] = page["nextPageToken"]
            else:
                break

    def get_presigned_url(self, bucket, key, expires_at, method="GET", headers=None, content_type=None, md5_b64=""):
        from cryptography.hazmat.backends import default_backend
        from cryptography.hazmat.primitives import serialization, hashes
        from cryptography.hazmat.primitives.asymmetric import padding

        string_to_sign = "\n".join([method, md5_b64, content_type or "", str(int(expires_at))])
        for header, value in (headers.items() if headers else {}):
            string_to_sign += "\n" + header + ":" + value
        string_to_sign += "\n/" + bucket + "/" + key
        private_key_bytes = self.config.service_credentials["private_key"].encode()
        private_key = serialization.load_pem_private_key(private_key_bytes, password=None, backend=default_backend())
        signature = private_key.sign(string_to_sign.encode(), padding.PKCS1v15(), hashes.SHA256())
        qs = dict(GoogleAccessId=self.config.service_credentials["client_email"],
                  Expires=str(int(expires_at)),
                  Signature=base64.b64encode(signature).decode())
        return self.presigned_url_base + bucket + "/" + key + "?" + requests.compat.urlencode(qs)

class GSUploadClient(GSClient):
    base_url = "https://www.googleapis.com/upload/storage/v1/"
