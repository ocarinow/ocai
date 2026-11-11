# Changelog

Releases are managed by the repository changeset workflow.
## 0.1.1 (2026-11-11)

### Features

#### Authenticate explicit AWS requests through the existing credential contract

Add SigV4Credential backed by AWS-maintained signing, with per-attempt request
isolation and no SDK objects in the public API. The AWS dependency stays in the
external ocai-aws package; core dependencies are unchanged. (WU-47, #106)

Extend the import-contract regression count for the explicit credential boundary;
no kernel runtime or dependency change.
