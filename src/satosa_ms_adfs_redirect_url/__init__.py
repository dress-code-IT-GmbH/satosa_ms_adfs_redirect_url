"""
ADFS/SAML-Support for role selection and profile completion after a SAML-Response
was issued using a redirect-to-idp flow.
* Store AuthnRequest for later replay
* Handle redirect-to-idp and replay AuthnRequest after redirect-to-idp flow

Persist state: Storing the the full context of the AuthnRequest in SATOSA_STATE is not feasible due to cookie size limitations.
Instead, it is stored in a local redis store, and the key is stored in SATOSA_STATE.

The Redis interface is using a basic implementation creating a connection pool and TCP sockets for each call, which is OK for the modest deployment.
(Instantiating a global connection pool across gunicorn worker threads would impose some additional complexity.)
The AuthnRequest is stored unencrypted with the assumption that a stolen request cannot do harm,
because the final Response will only be delivered to the metadata-specified ACS endpoint.


"""

from .redirect_url_request import RedirectUrlRequest
from .redirect_url_response import RedirectUrlResponse
