# Product Feedback — DRAFT (not yet submitted)

> **Status: DRAFT for the hackathon submission form's product-feedback
> fields.** Everything below is friction we actually hit while building
> this Alexa+ track entry (a self-hosted MCP server) in October 2026.
> We did **not** use Bedrock, Lambda, ASK CLI, or the Alexa developer
> console for this build, and this draft claims no feedback about them.
> Scope note: our server serves read-only public-domain data, so we
> evaluated account linking and decided it wasn't needed; feedback #2/#3
> is about that evaluation experience, not a linking implementation bug.

## 1. `pip install mcp` now installs SDK v2, which breaks the documented API

The first command every Python MCP tutorial — including community Alexa+
write-ups we learned from — tells you to run is `pip install mcp`, then
`from mcp.server.fastmcp import FastMCP`. As of this build, that installs
the 2.x line, where `mcp.server.fastmcp` no longer exists (renamed to
`mcp.server.mcpserver.MCPServer`, with other API changes). Every existing
Alexa+ MCP example we found (FitLog, Lowtide, FixIt and others) targets
the v1 API, so a new entrant's first run fails before they write a line of
their own code.

Credit where due: the v2 `ModuleNotFoundError` message itself explains the
rename and links the migration guide — that softened the landing a lot.
Ask: pin or call out the SDK major version on the Alexa+ MCP guidance
pages, so hackathon entrants start on the version the examples use. We
pinned `mcp>=1.20,<2` and documented why in `requirements.txt`.

## 2. There is no single canonical "Build an MCP server for Alexa+" checklist

To answer basic questions — which MCP spec version, which transport, what
auth is expected, how to test — we had to assemble the picture from:

- the Alexa+ account-linking requirements pages on developer.amazon.com
  (OAuth 2.0 authorization-code grant, PKCE, HTTPS on 443);
- community dev.to posts and GitHub READMEs from other entrants, which are
  where the operational gotchas actually live: spec pinned to 2025-11-25,
  Streamable HTTP, 401 responses must not carry a `WWW-Authenticate`
  header, RFC 9728 protected-resource metadata, and the fact that outside
  developers currently can't register a real Alexa+ add-on, so end-to-end
  testing happens against simulators.

Ask: one authoritative page that consolidates protocol version, transport,
auth tiers (including "public read-only data ⇒ no account linking
needed"), and the sanctioned way to test without a registered add-on. The
community is filling this gap today; an official version would retire a
lot of folklore risk.

## 3. Two near-duplicate account-linking requirement pages disagree in details

We found "Requirements for Account Linking" under both the Alexa+
documentation path and the general Alexa path. They are near-identical
but not identical — e.g. the note that Let's Encrypt certificates can't
be used ("even though it appears on the approved certificate list")
appears on one of them. When deciding our auth approach we couldn't tell
which page governs an Alexa+ MCP add-on. Ask: mark one as canonical for
Alexa+, or merge them.

## 4. MCP Python SDK (v1): dict-returning tools surface as empty structured results

FastMCP v1 tools that return a `dict` deliver the payload as text content;
clients that read only `structuredContent` see `{}` and conclude the tool
"returned nothing" (our first test client did exactly this). For a
hackathon where judges may test with assorted clients, this is a support
trap. Ask (for the SDK team): either populate `structuredContent` for
dict results by default, or make the behavior loud in the FastMCP docs.
Workaround used here: parse the text content as JSON in the test client.

## 5. What worked well

- The MCP spec's Streamable HTTP + stateless mode made the server
  trivially testable with the official SDK client — initialize, list
  tools, call tools, done.
- The v2 SDK's self-explaining import error (see #1) is a pattern worth
  keeping.
- Community entrants' public write-ups (linked from Devpost/DEV) were
  genuinely useful onboarding material; surfacing them from the official
  hackathon page would help the next cohort.
