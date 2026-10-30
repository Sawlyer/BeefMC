# HAProxy PROXY Protocol Support Matrix

Audit date: 2026-10-29

This inventory checks the local BeefMC branch refs for both a Netty `HAProxyMessageDecoder` and a `proxy-protocol` configuration marker. A source marker indicates inherited implementation is present in that branch; it does not prove that the branch builds or that runtime behavior was tested.

| Minecraft version | BeefMC branch | Source status | Config source | Full build | Runtime |
|---|---|---|---|---|---|
| 1.8.8 | `version/1.8.8` | BeefMC patch applied | `beefmc.yml` | Full build not checked | Runtime not checked |
| 1.9.4 | `version/1.9.4` | Missing | Not implemented | Not checked | Not checked |
| 1.10.2 | `version/1.10.2` | Missing | Not implemented | Not checked | Not checked |
| 1.11.2 | `version/1.11.2` | Missing | Not implemented | Not checked | Not checked |
| 1.12.2 | `version/1.12.2` | Missing | Not implemented | Not checked | Not checked |
| 1.13.2 | `version/1.13.2` | Missing | Not implemented | Not checked | Not checked |
| 1.14 | `version/1.14` | Missing | Not implemented | Not checked | Not checked |
| 1.15.2 | `version/1.15.2` | Missing | Not implemented | Not checked | Not checked |
| 1.16.5 | `version/1.16.5` | Missing | Not implemented | Not checked | Not checked |
| 1.17.1 | `version/1.17.1` | Missing | Not implemented | Not checked | Not checked |
| 1.18.2 | `version/1.18.2` | Inherited Paper implementation | Paper config; BeefMC override pending | Not checked | Not checked |
| 1.19.4 | `version/1.19.4` | Inherited Paper implementation | Paper config; BeefMC override pending | Not checked | Not checked |
| 1.20.4 | `version/1.20.4` | Inherited Paper implementation | Paper config; BeefMC override pending | Not checked | Not checked |
| 1.20.6 | `version/1.20.6` | Inherited Paper implementation | Paper config; BeefMC override pending | Not checked | Not checked |
| 1.21.1 | `version/1.21.1` | Inherited Paper implementation | Paper config; BeefMC override pending | Not checked | Not checked |
| 1.21.3 | `version/1.21.3` | Inherited Paper implementation | Paper config; BeefMC override pending | Not checked | Not checked |
| 1.21.4 | `version/1.21.4` | Inherited Paper implementation | Paper config; BeefMC override pending | Not checked | Not checked |
| 1.21.5 | `version/1.21.5` | Inherited Paper implementation | Paper config; BeefMC override pending | Not checked | Not checked |
| 1.21.8 | `version/1.21.8` | Inherited Paper implementation | Paper config; BeefMC override pending | Not checked | Not checked |
| 1.21.9 | `version/1.21.9` | Inherited Paper implementation | Paper config; BeefMC override pending | Not checked | Not checked |
| 1.21.10 | `version/1.21.10` | Inherited Paper implementation | Paper config; BeefMC override pending | Not checked | Not checked |
| 1.21.11 | `version/1.21.11` | Inherited Paper implementation | Paper config; BeefMC override pending | Not checked | Not checked |
| 26.1.2 | `version/26.1.2` | Inherited Paper implementation | Paper config; BeefMC override pending | Not checked | Not checked |
| 26.2 | `version/26.2` | Inherited Paper implementation | Paper config; BeefMC override pending | Not checked | Not checked |
| 26.3 | `main` | Inherited Paper implementation | Paper config; BeefMC override pending | Not checked | Not checked |

## Audit method

- Inspected all 24 local `origin/version/*` refs and `origin/main`.
- Missing support means neither decoder nor configuration marker was found in Java, patch, YAML, or YML files.
- Inherited support means both decoder and configuration markers were found in the branch. Existing Paper behavior remains authoritative.
- This inventory is a source audit only. Build, protocol tests, and runtime interoperability remain separate checks.
- The 1.8.8 patch stack applied cleanly. Changed Java sources compiled directly against existing branch outputs, and six focused JUnit tests passed. The full Gradle build and live HAProxy check remain unverified.

## Rollout

1.8.8 now reads its opt-in setting from `beefmc.yml`; it copies legacy `pandaspigot.yml` on first start when needed and keeps the old command-line alias. The patch stack applies cleanly. Legacy 1.9.4–1.17.1 still need backports; modern branches still need their setting routed from Paper config to `beefmc.yml`. Keep each branch's build and runtime status explicit until its own checks pass.
