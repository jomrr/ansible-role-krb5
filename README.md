# Ansible Role: krb5

![GitHub](https://img.shields.io/github/license/jomrr/ansible-role-krb5)
![GitHub last commit](https://img.shields.io/github/last-commit/jomrr/ansible-role-krb5)
![GitHub issues](https://img.shields.io/github/issues-raw/jomrr/ansible-role-krb5)
[![dev](https://img.shields.io/github/actions/workflow/status/jomrr/ansible-role-krb5/dev.yml?branch=dev&label=dev)](https://github.com/jomrr/ansible-role-krb5/actions/workflows/dev.yml?query=branch%3Adev)
[![main](https://img.shields.io/github/actions/workflow/status/jomrr/ansible-role-krb5/main.yml?branch=main&label=main)](https://github.com/jomrr/ansible-role-krb5/actions/workflows/main.yml?query=branch%3Amain)

Configure MIT Kerberos clients for domain members and standalone GSSAPI
acceptors.

## Purpose

Provide the system Kerberos configuration for AD members and standalone services
accepting GSSAPI tickets.

## Scope

### Managed

- Kerberos client packages on Fedora, AlmaLinux, Debian, Ubuntu, openSUSE Leap
  and Tumbleweed.
- /etc/krb5.conf and the /etc/krb5.conf.d directory, preserving existing
  snippets.
- Default realm, platform credential cache, optional default keytab path, DNS
  discovery and domain mappings.

### Not Managed

- Domain joins, machine accounts, keytab contents or permissions, service
  configuration and service restarts.
- Explicit KDC entries, DNS resolver configuration and clock synchronization.
- Domain controllers; samba_ad_dc continues to install Samba's generated
  Kerberos configuration there.

## Requirements

- Run krb5 before samba_ad_sssd or samba_ad_member in the playbook, using the
  same realm.
- Domain members need working DNS SRV discovery for their KDCs.
- Standalone HTTP GSSAPI acceptors need an HTTP service principal and matching
  keytab supplied by the httpd role.

## Dependencies

```yaml
collections:
  - name: community.general
    version: '>=12.0.0'
```

## Role Variables

### `krb5_realm`

Type: `str`. Required: `true`.

Default Kerberos realm and DNS domain for explicit realm mappings.

### `krb5_dns_lookup_kdc`

Type: `bool`. Required: `false`.

Discover KDCs through DNS SRV records; disable for standalone GSSAPI acceptors.

Default:

```yaml
krb5_dns_lookup_kdc: true
```

### `krb5_default_keytab`

Type: `path`. Required: `false`.

Optional Kerberos library default keytab path; the role does not create or
manage keytabs.

## Managed Files

- `/etc/krb5.conf (root:root, mode 0644, complete file with backup)`
- `/etc/krb5.conf.d (root:root, mode 0755, existing snippets preserved)`

## Check Mode

Supported through the native package, file and template modules.

## Service Behavior

No daemon or consumer restart is managed by this role.

## Security Notes

- DNS realm lookup, DNS hostname canonicalization and reverse DNS lookup are
  disabled.
- Distribution crypto-policy snippets remain available; the role does not pin
  encryption algorithms.
- The default keytab variable selects a library path only. Its owning service or
  join role manages the keytab.

## Operational Notes

- The default realm is uppercase. Its DNS domain and subdomains are mapped in
  lowercase to that realm.
- The includedir directive is last. MIT Kerberos uses the first value for
  single-valued relations, so the managed settings take precedence over snippets
  such as sssd-kcm's kcm_default_ccache. Snippets supply settings that this role
  leaves unset. The include directory is created before writing the
  configuration.
- Credential caches use FILE:/tmp/krb5cc_%{uid} on Debian/Ubuntu and
  KEYRING:persistent:%{uid} on Red Hat/openSUSE.
- If krb5_default_keytab is unset, default_keytab_name is omitted. Without a
  snippet or environment override, the library uses its platform default,
  normally FILE:/etc/krb5.keytab. No keytab is created by this role.
- samba_ad_member with kerberos method=secrets and keytab writes to the library
  default keytab. Set krb5_default_keytab and samba_ad_member_keytab_path to the
  same path when choosing a non-default location. SSSD and adcli use
  samba_ad_sssd_keytab explicitly and do not require krb5_default_keytab.
- A DMZ HTTP service can accept client service tickets using its own keytab
  without joining AD or contacting a KDC. Set krb5_dns_lookup_kdc=false and
  leave krb5_default_keytab unset; configure the service keytab in httpd.
  Obtaining tickets or performing delegation is a separate client operation and
  may require KDC access.
- No standalone configuration validator is provided by the installed Kerberos
  client tools. Native library resolution is covered by the integration tests;
  domain joins and authentication are covered by the consumers.

## Supported Platforms

| OS Family | Distribution | Version | Container Image |
| --------- | ------------ | ------- | --------------- |
| RedHat | AlmaLinux | latest | [jomrr/molecule-almalinux:latest](https://hub.docker.com/r/jomrr/molecule-almalinux) |
| Debian | Debian | latest | [jomrr/molecule-debian:latest](https://hub.docker.com/r/jomrr/molecule-debian) |
| RedHat | Fedora | latest | [jomrr/molecule-fedora:latest](https://hub.docker.com/r/jomrr/molecule-fedora) |
| Suse | OpenSuse Leap | latest | [jomrr/molecule-opensuse-leap:latest](https://hub.docker.com/r/jomrr/molecule-opensuse-leap) |
| Suse | OpenSuse Tumbleweed | latest | [jomrr/molecule-opensuse-tumbleweed:latest](https://hub.docker.com/r/jomrr/molecule-opensuse-tumbleweed) |
| Debian | Ubuntu | latest | [jomrr/molecule-ubuntu:latest](https://hub.docker.com/r/jomrr/molecule-ubuntu) |

## Example Playbook

### SSSD domain member

Configure Kerberos before joining; SSSD manages its own explicit keytab path.

```yaml
---
- name: Configure AD logins
  hosts: workstations
  gather_facts: true
  roles:
    - role: jomrr.krb5
      krb5_realm: AD.EXAMPLE.COM
    - role: jomrr.samba_ad_sssd
      samba_ad_sssd_realm: AD.EXAMPLE.COM
      samba_ad_sssd_join_password: "{{ vault_ad_join_password }}"
```

### Samba member with an explicit system keytab

Keep the library default and Samba's managed keytab path aligned.

```yaml
---
- name: Configure file servers
  hosts: fileservers
  gather_facts: true
  roles:
    - role: jomrr.krb5
      krb5_realm: AD.EXAMPLE.COM
      krb5_default_keytab: /etc/samba/member.keytab
    - role: jomrr.samba_ad_member
      samba_ad_member_realm: AD.EXAMPLE.COM
      samba_ad_member_domain: EXAMPLE
      samba_ad_member_server: dc1.ad.example.com
      samba_ad_member_keytab_path: /etc/samba/member.keytab
      samba_ad_member_join_password: "{{ vault_ad_join_password }}"
```

### Standalone DMZ HTTP acceptor

The httpd role supplies its service keytab and GSSAPI configuration separately.

```yaml
---
- name: Configure Kerberos for a DMZ web service
  hosts: dmz_webservers
  gather_facts: true
  roles:
    - role: jomrr.krb5
      krb5_realm: AD.EXAMPLE.COM
      krb5_dns_lookup_kdc: false
```

## References

- [MIT Kerberos configuration](https://web.mit.edu/kerberos/krb5-latest/doc/admin/conf_files/krb5_conf.html)
- [MIT GSSAPI acceptor credentials](https://web.mit.edu/kerberos/krb5-latest/doc/appdev/gssapi.html#acceptor-credentials)

## Author

[Jonas Mauer](https://github.com/jomrr)

## License

This project is licensed under the MIT License.
See [LICENSE](LICENSE) for the full license text.

Copyright (c) 2026 Jonas Mauer.
