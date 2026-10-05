#!/usr/bin/env python3
"""Check effective system settings through MIT Kerberos, including include order."""

import argparse
import ctypes
import json
import os


def check_status(status: int) -> None:
    """Report native failures without substituting parser defaults."""
    if status:
        raise RuntimeError(f"MIT Kerberos returned error {status}")


class KerberosConfig:
    """Read the same configuration and defaults as Kerberos applications."""

    def __init__(self) -> None:
        self.library = ctypes.CDLL("libkrb5.so.3")
        pointer = ctypes.c_void_p
        string = ctypes.c_char_p
        signatures = (
            ("krb5_init_context", [ctypes.POINTER(pointer)], ctypes.c_int),
            ("krb5_get_profile", [pointer, ctypes.POINTER(pointer)], ctypes.c_int),
            ("krb5_cc_default_name", [pointer], string),
            ("krb5_kt_default_name", [pointer, string, ctypes.c_int], ctypes.c_int),
            ("krb5_free_context", [pointer], None),
            ("profile_get_string", [pointer, string, string, string, string,
                                    ctypes.POINTER(string)], ctypes.c_long),
            ("profile_release_string", [string], None),
            ("profile_release", [pointer], None),
        )
        for name, arguments, result in signatures:
            function = getattr(self.library, name)
            function.argtypes = arguments
            function.restype = result
        self.context = pointer()
        self.profile = pointer()
        check_status(self.library.krb5_init_context(ctypes.byref(self.context)))
        check_status(self.library.krb5_get_profile(self.context, ctypes.byref(self.profile)))

    def read(self, section: str, relation: str) -> str | None:
        """Return the library's first effective relation value."""
        value = ctypes.c_char_p()
        check_status(self.library.profile_get_string(
            self.profile, section.encode(), relation.encode(), None, None, ctypes.byref(value)
        ))
        try:
            return ctypes.string_at(value).decode() if value.value is not None else None
        finally:
            self.library.profile_release_string(value)

    def settings(self, realm: str) -> dict[str, str | None]:
        """Read effective relations and library-resolved credential locations."""
        keytab = ctypes.create_string_buffer(1024)
        check_status(self.library.krb5_kt_default_name(self.context, keytab, len(keytab)))
        result = {
            relation: self.read("libdefaults", relation)
            for relation in (
                "default_realm", "dns_lookup_kdc", "dns_lookup_realm",
                "dns_canonicalize_hostname", "rdns", "ticket_lifetime",
            )
        }
        result.update({
            "default_ccache_name": self.library.krb5_cc_default_name(self.context).decode(),
            "default_keytab_name": keytab.value.decode(),
            "domain": self.read("domain_realm", realm.lower()),
            "subdomains": self.read("domain_realm", "." + realm.lower()),
        })
        return result

    def close(self) -> None:
        """Release native configuration objects."""
        self.library.profile_release(self.profile)
        self.library.krb5_free_context(self.context)


def main() -> None:
    """Compare application-visible results for a member or DMZ configuration."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--realm", required=True)
    parser.add_argument("--ccache-type", choices=("FILE", "KEYRING"), required=True)
    parser.add_argument("--keytab", required=True)
    parser.add_argument("--dns-lookup-kdc", choices=("true", "false"), required=True)
    arguments = parser.parse_args()
    cache = (f"FILE:/tmp/krb5cc_{os.getuid()}" if arguments.ccache_type == "FILE"
             else f"KEYRING:persistent:{os.getuid()}")
    expected = {
        "default_realm": arguments.realm.upper(),
        "default_ccache_name": cache,
        "default_keytab_name": "FILE:" + arguments.keytab,
        "dns_lookup_kdc": arguments.dns_lookup_kdc,
        "dns_lookup_realm": "false",
        "dns_canonicalize_hostname": "false",
        "rdns": "false",
        "ticket_lifetime": "10h",
        "domain": arguments.realm.upper(),
        "subdomains": arguments.realm.upper(),
    }
    config = KerberosConfig()
    try:
        actual = config.settings(arguments.realm)
    finally:
        config.close()
    if actual != expected:
        raise SystemExit(f"Unexpected Kerberos settings: {actual!r}; expected: {expected!r}")
    print(json.dumps(actual, sort_keys=True))


if __name__ == "__main__":
    main()
