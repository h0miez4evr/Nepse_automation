"""
NEPSE API Authentication Module

Handles the complex WASM-based token transformation required by NEPSE's API.
The API uses a WebAssembly module (css.wasm) to transform access tokens
before they can be used for authenticated requests.
"""

import os
import hashlib
import requests
from wasmtime import Engine, Module, Store, Instance


class NepseAuth:
    """
    Authenticates with the NEPSE API using WASM-based token transformation.
    
    The NEPSE API requires:
    1. Fetching an access token from /api/authenticate/prove
    2. Transforming the token using WASM functions (cdx, rdx, bdx, ndx, mdx)
       that rearrange characters based on salt values
    3. Using the transformed token in Authorization: Salter <token> header
    """

    BASE_URL = "https://www.nepalstock.com.np"
    AUTH_ENDPOINT = "/api/authenticate/prove"
    WASM_URL = "/assets/prod/css.wasm"

    def __init__(self):
        self.engine = Engine()
        self.wasm_module = None
        self.store = None
        self.instance = None
        self._load_wasm()

    def _load_wasm(self):
        """Download and instantiate the NEPSE WASM module."""
        # Check if we have a cached WASM file
        wasm_cache = os.path.join(os.path.dirname(__file__), "css.wasm")

        if not os.path.exists(wasm_cache):
            print("[Auth] Downloading NEPSE WASM module...")
            resp = requests.get(
                f"{self.BASE_URL}{self.WASM_URL}",
                headers={"User-Agent": "Mozilla/5.0"},
            )
            resp.raise_for_status()
            with open(wasm_cache, "wb") as f:
                f.write(resp.content)
            print(f"[Auth] WASM module cached ({len(resp.content)} bytes)")

        self.wasm_module = Module.from_file(self.engine, wasm_cache)
        self.store = Store(self.engine)
        self.instance = Instance(self.store, self.wasm_module, [])

    def _get_wasm_exports(self):
        """Get the WASM exported functions for token transformation."""
        exports = self.instance.exports(self.store)
        return {
            "cdx": exports["cdx"],
            "rdx": exports["rdx"],
            "bdx": exports["bdx"],
            "ndx": exports["ndx"],
            "mdx": exports["mdx"],
        }

    def _transform_token(self, access_token, salt1, salt2, salt3, salt4, salt5):
        """
        Transform access token using WASM functions.
        
        The transformation rearranges characters in the token string
        based on indices computed by WASM functions using salt values.
        This replicates the browser's JavaScript transformation logic.
        """
        wasm = self._get_wasm_exports()

        # Compute indices using WASM functions
        # Note: argument order differs for rdx/bdx/ndx/mdx (s3 and s4 are swapped)
        c1 = wasm["cdx"](self.store, salt1, salt2, salt3, salt4, salt5)
        r1 = wasm["rdx"](self.store, salt1, salt2, salt4, salt3, salt5)
        b1 = wasm["bdx"](self.store, salt1, salt2, salt4, salt3, salt5)
        n1 = wasm["ndx"](self.store, salt1, salt2, salt4, salt3, salt5)
        m1 = wasm["mdx"](self.store, salt1, salt2, salt4, salt3, salt5)

        # Rearrange token characters at computed index positions
        # This slices and concatenates the token to create the transformed version
        transformed = (
            access_token[:c1]
            + access_token[c1 + 1 : r1]
            + access_token[r1 + 1 : b1]
            + access_token[b1 + 1 : n1]
            + access_token[n1 + 1 : m1]
            + access_token[m1 + 1 :]
        )
        return transformed

    def get_authenticated_session(self):
        """
        Create and return an authenticated requests session.
        
        Returns:
            requests.Session: A session with valid Authorization header.
        """
        session = requests.Session()
        session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
                "Accept": "application/json, text/plain, */*",
                "Referer": f"{self.BASE_URL}/",
            }
        )

        # Step 1: Get auth token from NEPSE API
        print("[Auth] Fetching authentication token...")
        auth_resp = session.get(f"{self.BASE_URL}{self.AUTH_ENDPOINT}")
        auth_resp.raise_for_status()
        auth_data = auth_resp.json()

        access_token = auth_data["accessToken"]
        salt1 = auth_data["salt1"]
        salt2 = auth_data["salt2"]
        salt3 = auth_data["salt3"]
        salt4 = auth_data["salt4"]
        salt5 = auth_data["salt5"]

        # Step 2: Transform token using WASM functions
        print("[Auth] Transforming token using WASM module...")
        transformed_token = self._transform_token(
            access_token, salt1, salt2, salt3, salt4, salt5
        )

        # Step 3: Set authorization header
        session.headers.update({"Authorization": f"Salter {transformed_token}"})
        print("[Auth] Authentication successful!")
        return session
