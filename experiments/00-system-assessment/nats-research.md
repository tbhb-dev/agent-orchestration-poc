# NATS assumptions verified against source

Verified on 2026-09-26 against `nats-server` HEAD 3e8ddaa7 (v2.15.0 plus 83 commits, `server/const.go:69` reports `VERSION = "2.16.0-dev"`), `nats.go` HEAD 5adc9d5d (v1.54.0 plus 2 commits), and `nats-architecture-and-design` HEAD 68574339. Paths below are relative to each repo root. Minimum versions marked "git" come from the first release tag containing the commit that introduced the identifier, found with `git log -S` and `git describe --contains`. The server repo carries no changelog file. Its `RELEASES.md` describes the process only, so release-note facts come from `docs.nats.io` pages and ADR release-history tables and are labelled accordingly.

## Summary table

| # | Assumption | Verdict | Minimum server | Primary source |
| --- | --- | --- | --- | --- |
| 1 | Embedded server with JetStream and in-process clients | True | v2.9.0 for `InProcessConn` and `DontListen` (git) | `server/server.go:708,2267,2886,4061`, `nats.go:305-319,1140` |
| 2 | Multi-filter durable pull consumers, `Fetch` expiry, `MaxWaiting`, disconnect handling | True, with constraints | v2.10.0 for `FilterSubjects` (git) | `server/consumer.go:101,670-672,886-913,4520`, `jetstream/pull.go:839` |
| 3 | Explicit ack, `AckWait`, `MaxDeliver`, nak with delay | True | v2.7.1 for nak delay (git) | `server/consumer.go:351-361,597-618,3281-3300` |
| 4 | Dedup by `Nats-Msg-Id` within `Duplicates` window | True. Default 2m. No fixed maximum, capped by `MaxAge` and an optional operator limit | v2.2.0 (git) | `server/stream.go:67,737,1886,1988-2016` |
| 5 | Arbitrary headers on JetStream messages and core request-reply | True | Headers since server 2.2 per ADR-4 | ADR-4, `nats.go:4439,4833` |
| 6 | KV create, compare-and-set, history, per-key TTL, bucket TTL | True. Per-key TTL only on `Create`, needs `LimitMarkerTTL` on the bucket | v2.11.0 for per-message and per-key TTL | `jetstream/kv.go`, `jetstream/kv_options.go:126`, ADR-43, ADR-48 |
| 7 | Accounts as isolation, per-user allow lists, `{{name()}}` templates, per-account JetStream limits | Partially. Templates work only for JWT scoped signing keys and auth callout, not static config users | Templates v2.2.0, callout v2.10.0 (git) | `server/accounts.go:49-50`, `server/auth.go:479-560,1037-1049`, `server/jetstream.go:71-78` |
| 8 | Nkeys, decentralized JWT, `.creds`, auth callout and what it sees | True. Callout sees connection metadata, credentials, and TLS state only. No process information | v2.10.0 for auth callout (git, docs) | `server/auth_callout.go:30,383-400,456-501`, ADR-26 |
| 9 | Leaf node with own JetStream needs a domain; hub can reach leaf streams | True with a nuance. Without a domain and with a shared system account the leaf extends the hub's JetStream instead | Domains since v2.2.3 (git); 2.15 adds domain-prefixed API in the system account | `server/leafnode.go:2035-2124`, `server/jetstream_api.go:371-388`, ADR-19 |
| 10 | Client TLS yes, Unix domain socket no | True | n/a | `server/util.go:273`, `server/server.go:2879,2968`, `server/opts.go:5144-5232` |
| 11 | Ordered consumers for observation; `NumPending` and `NumAckPending` in consumer info | True | n/a | `jetstream/ordered.go:631-645`, `server/consumer.go:57-69`, ADR-17 |
| 12 | Max payload default, per-account storage and stream limits, per-user connection limits | Partially. Payload default 1 MiB, account limits exist, but connection-count limits are per account or per server, not per user | n/a | `server/const.go:94`, `server/opts.go:3599,1365,2420-2463` |
| 13 | Current stable and 2.11 to 2.15 changes | Current stable is v2.15.0, released 2026-09-17. 2.13 was never released | n/a | `git tag`, `RELEASES.md`, docs release notes, ADR index |

## 1. Embedded server and in-process clients

Verdict: true. The Go package is `github.com/nats-io/nats-server/v2/server`. The client packages are `github.com/nats-io/nats.go` for the core connection and `github.com/nats-io/nats.go/jetstream` for the JetStream API (the `jetstream` package first appeared in nats.go v1.26.0, git).

[source] `server/server.go:708` defines `func NewServer(opts *Options) (*Server, error)`. The comment at lines 704-707 says the provided `Options` must not be reused afterwards; pass `Options.Clone()` or a fresh struct.

[source] `server/server.go:2267` defines `func (s *Server) Start()`. `server/server.go:2588` defines `Shutdown()`, and `server/server.go:2778` defines `WaitForShutdown()`. `server/service.go:20` defines `Run(server *Server) error` as the signal-handling wrapper the binary uses.

[source] `server/server.go:4061` defines `func (s *Server) ReadyForConnections(dur time.Duration) bool`. The readiness check at `server/server.go:4007` treats the server as ready when either the listener exists or `opts.DontListen` is set, so readiness works for a no-listener embedded server.

[source] `server/server.go:2886` defines `func (s *Server) InProcessConn() (net.Conn, error)`, which builds a `net.Pipe` and runs `createClientInProcess` on the server side. The comment at lines 2882-2885 states it works regardless of `DontListen`. `server/opts.go:420` defines `DontListen bool` (json `dont_listen`). Both `InProcessConn` and `DontListen` were introduced by commit e9abc580, first released in v2.9.0 (git).

[source] `nats.go:305-307` defines `type InProcessConnProvider interface { InProcessConn() (net.Conn, error) }`, which `*server.Server` satisfies. `nats.go:316-319` defines `Options.InProcessServer`, `nats.go:1140` defines the `nats.InProcessServer(server)` option (first in nats.go v1.17.0, git), and `nats.go:2470-2477` shows `createConn` using it instead of dialing. `nats.go:2464-2466` still requires a server URL entry to exist, so pass any URL string (the default is fine); it is not dialed when `InProcessServer` is set.

[source] JetStream options on `server.Options`: `JetStream bool` at `server/opts.go:465`, `JetStreamMaxMemory int64` and `JetStreamMaxStore int64` at 467-468, `JetStreamDomain string` at 469, `JetStreamKey string` (encryption at rest) at 471, `StoreDir string` at 486, `SyncInterval time.Duration` at 487. `NoLog` and `NoSigs` at 428-429 are the usual embedding flags. Unset memory and store limits default to -1, meaning unlimited, at `server/opts.go:6186-6190`.

[source] Storage directory: `server/jetstream.go:234` appends the constant `JetStreamStoreDir = "jetstream"` (`server/jetstream.go:2792`) under `StoreDir`, and `server/jetstream.go:2805-2808` falls back to `os.TempDir()/nats/jetstream` when `StoreDir` is empty. Set `StoreDir` explicitly for a daemon. `server/jetstream.go:207` also exposes `func (s *Server) EnableJetStream(config *JetStreamConfig) error`, and `JetStreamConfig` (`server/jetstream.go:43-52`) carries `MaxMemory`, `MaxStore`, `StoreDir`, `SyncInterval`, `SyncAlways`, `Domain`, `Strict`.

Caveat: in-process connections skip TLS and the TCP listener entirely, but authentication and account permissions still apply because `createClientInProcess` runs the normal client path.

## 2. Multi-filter pull consumers, Fetch with expiry, MaxWaiting, disconnects

Verdict: true, with server-enforced constraints.

[source] `server/consumer.go:100-101` defines `FilterSubject string` (json `filter_subject`) and `FilterSubjects []string` (json `filter_subjects`). `FilterSubjects` first shipped in v2.10.0 (commit af338d0d, git). [adr] ADR-34 "JetStream Consumers Multiple Filters" is the design document; it does not state a version.

[source] Constraints at consumer creation: setting both `FilterSubject` and `FilterSubjects` is rejected (`server/consumer.go:886-890`), an empty string entry is rejected (897-901), and filters that overlap each other are rejected with `NewJSConsumerOverlappingSubjectFiltersError` (903-913). On a work-queue retention stream, filters must also be partition-unique across all consumers of the stream (`server/consumer.go:1131-1137`).

[source] Pull request handling is `processNextMsgRequest` at `server/consumer.go:4678`. Server-side rejections are sent as status messages: `409 Consumer is push based` (4693), `409 Exceeded MaxRequestBatch` (4706), `409 Exceeded MaxRequestExpires` (4711), `409 Exceeded MaxRequestMaxBytes` (4716), `409 Exceeded MaxWaiting` (4798 and 4809), `408 Requests Pending` for a no-wait request that must queue (4778). The `MaxWaiting` 409 is suppressed when the request carries a heartbeat interval, to avoid a hot retry loop (comment at 4805-4808). Expiry produces `408 Request Timeout` carrying the headers `Nats-Pending-Messages` and `Nats-Pending-Bytes` (`server/consumer.go:44-46`, 4539, 5124). A completed batch with bytes remaining yields `409 Batch Completed` (54). Leadership change and consumer deletion send `409 Leadership Change` (3221) and `409 Consumer Deleted` (3238).

[source] `MaxWaiting` is `ConsumerConfig.MaxWaiting int` (json `max_waiting`, `server/consumer.go:105`). For pull consumers a zero value defaults to `JSWaitQueueDefaultMax = 512` (`server/jetstream_api.go:848`, applied at `server/consumer.go:670-672`). Negative values are zeroed or rejected in pedantic mode (620-625). No upper cap is enforced in that validation block. Related per-consumer request caps are `MaxRequestBatch`, `MaxRequestExpires`, and `MaxRequestMaxBytes` (`server/consumer.go:111-113`), and the server-wide `jetstream { limits { max_request_batch } }` (`server/opts.go:2549-2550`) forces a batch cap onto consumers that did not set one (708-712).

[source] Disconnect behaviour: each waiting request records the reply subject and the account and subject where interest lives (`trackDownAccountAndInterest`, `server/consumer.go:4787-4791`). When the consumer processes its wait queue, it drops any request whose interest is gone, tested with `wr.acc.sl.HasInterest(wr.interest)` at `server/consumer.go:4520`, plus a gateway-interest check at 4524. If the request had crossed an account export it also sends `408 Interest Expired` (4554-4557). So a fetch pending for a client that disconnected is removed at the next wait-queue pass, and no message is delivered to it. [adr] ADR-13 line 68-69 states a pull request "will linger until there is no more interest in the subject, a client is disconnected or the batch size is filled", and ADR-37 revision 3 (2026-02-10) records the addition of `408 Interest Expired`.

[source] Client side in nats.go: `func (p *pullConsumer) Fetch(batch int, opts ...FetchOpt) (MessageBatch, error)` at `jetstream/pull.go:839`, `FetchBytes` at 872, `FetchNoWait` at 908, `Next` at 1043, and the long-running `Consume` (202) and `Messages` (504). `FetchMaxWait(timeout)` at `jetstream/jetstream_options.go:527` sets the request `expires`, defaulting to 30 seconds (comment at 525). `FetchHeartbeat` at 546 documents that a heartbeat of 5 seconds is enabled automatically when the max wait exceeds 10 seconds, and `ErrNoHeartbeat` (`jetstream/errors.go:316`) fires after two missed heartbeats. `Fetch` returns a `MessageBatch` whose channel closes at expiry; messages already sent by the server are still consumed. Error mapping for status codes is in `jetstream/pull.go:739-750` (`ErrBatchCompleted`, `ErrConsumerDeleted`, `ErrConsumerLeadershipChanged`, `ErrMaxBytesExceeded`).

Caveat: ADR-13 line 37 says the client library imposes no batch limit, but the server-wide `max_request_batch` limit and the per-consumer `MaxRequestBatch` do.

## 3. Explicit acknowledgment, AckWait, MaxDeliver, nak with delay

Verdict: true.

[source] `server/consumer.go:351-361` defines `AckPolicy` with `AckNone`, `AckAll`, `AckExplicit`, and `AckFlowControl` (json values `none`, `all`, `explicit`; the flow-control policy is for asynchronous replication and arrived in 2.14 per the docs, see item 13). In nats.go the constants are `AckExplicitPolicy` (the default), `AckAllPolicy`, `AckNonePolicy`, `AckFlowControlPolicy` at `jetstream/consumer_config.go:492-503`.

[source] `AckWait` (json `ack_wait`) and `MaxDeliver` (json `max_deliver`) are at `server/consumer.go:97-98`. Defaults: `AckWait` becomes `JsAckWaitDefault = 30 * time.Second` (597, applied at 674-676) for explicit and all policies; `MaxDeliver` zero becomes -1, meaning unlimited (613-618). `BackOff []time.Duration` (99) overrides `AckWait` with its first element and requires `MaxDeliver` to cover the list (677-696). `MaxAckPending` defaults to `JsDefaultMaxAckPending = 1000` (604, 697-699). Redelivery is driven by the pending timer `resetPtmr` at 7295-7303 and `checkPending`, so an unacked message is redelivered after `AckWait` until `MaxDeliver` is hit. Hitting the limit emits the advisory `io.nats.jetstream.advisory.v1.max_deliver` (`server/jetstream_events.go:120-132`).

[source] Ack protocol payloads are `+ACK` (empty payload also acks), `-NAK`, `+WPI` (in progress, resets the ack timer), `+NXT`, and `+TERM` (`server/consumer.go:399-412`). A nak delay is either `-NAK <Go duration>` or `-NAK {"delay": <nanoseconds>}` via `ConsumerNakOptions{Delay time.Duration}` (236-238); parsing is at 3281-3300 and the delayed redelivery is scheduled by shifting the pending timestamp (3302-3306). The JSON form was introduced by commit 65b168aa, first in v2.7.1 (git).

[source] nats.go message methods: `Ack`, `DoubleAck(ctx)`, `Nak`, `NakWithDelay(delay)`, `InProgress`, `Term`, `TermWithReason(reason)` at `jetstream/message.go:359-401`.

## 4. Deduplication by Nats-Msg-Id

Verdict: true. Default window 2 minutes. There is no fixed maximum in the server; the effective ceiling is the stream `MaxAge` and, if the operator sets one, a server-wide limit.

[source] The header constant `JSMsgId = "Nats-Msg-Id"` is at `server/stream.go:737`; `StreamConfig.Duplicates time.Duration` (json `duplicate_window`) at 67; the dedup map and window at 589-590; the lookup `checkMsgId` at 5579; and the publish ack reports `Duplicate bool` (json `duplicate`) at 264. Both the header and the `duplicate_window` field first shipped in v2.2.0 (git, commits a50f9646 and ba9dd375).

[source] Defaults and bounds at `server/stream.go:1885-2016`: `StreamDefaultDuplicatesWindow = 2 * time.Minute` (1886). When `Duplicates` is zero on a non-mirror non-sourced stream, the window becomes the smaller of 2 minutes and `MaxAge` (1988-2003), and is further reduced to the operator limit if set (1990-1995). Explicit values are rejected if negative (2005), greater than `MaxAge` (2009), greater than the operator limit (2012-2014), or below 100 milliseconds (2016).

[source] The operator limit is `JetStreamLimits.Duplicates` (json `max_duplicate_window`, `server/opts.go:379`), configured as `jetstream { limits { duplicate_window: "<dur>" } }` (`server/opts.go:2554-2555`). It is unset by default.

[adr] ADR-50 line 94: atomic batch publishes rejected `Nats-Msg-Id` at first; from 2.12.1 dedup is supported inside batches and a batch with a duplicate is rejected as a whole.

## 5. Headers and core request-reply

Verdict: true.

[adr] ADR-4 "NATS Message Headers" defines the `NATS/1.0` header block, the `HPUB` and `HMSG` protocol verbs (lines 88-123), and states headers are case preserving (line 58). Arbitrary keys such as `Correlation-Id` are allowed; only `Nats-` prefixed keys carry server meaning (for JetStream see `server/stream.go:737-751`). The server can be built without header support via `Options.NoHeaderSupport` (`server/server.go:4068-4073`), so keep that unset.

[source] Header bytes count toward `max_payload`: `processHeaderPub` at `server/client.go:2926` parses the header length (2957, 2964) and the total size is checked against the client's max payload, with `maxPayloadViolation` at 2617 sending `Maximum Payload Violation`.

[source] nats.go: `type Header map[string][]string` at `nats.go:4439`, `NewMsg(subject)` at 4479, `PublishMsg` at 4572 (returns `ErrHeadersNotSupported`, line 150, against an old server). Request-reply: `Request(subj, data, timeout)` at 4833, `RequestMsg(msg, timeout)` at 4819 for requests with headers, and `ErrNoResponders` (152) is returned when the server answers with the `503` no-responders status (4859-4860). JetStream messages expose headers through `jetstream.Msg.Headers()` and the server stores them with the message.

## 6. Key-value buckets

Verdict: true, with two precise points. Per-key TTL is a create-time option only and requires `LimitMarkerTTL` on the bucket, which requires server 2.11 (API level 1). Bucket-level TTL maps to stream `MaxAge`.

[source] The `KeyValue` interface in `jetstream/kv.go` (lines 95-215) has `Get`, `GetRevision`, `Put`, `PutString`, `Create(ctx, key, value, opts ...KVCreateOpt) (uint64, error)`, `Update(ctx, key, value, revision uint64) (uint64, error)`, `Delete(ctx, key, opts ...KVDeleteOpt)`, `Purge`, `Watch`, `WatchAll`, `WatchFiltered`, `Keys`, `ListKeys`, `History(ctx, key, opts ...WatchOpt) ([]KeyValueEntry, error)`, `PurgeDeletes`, `Status`. Bucket management is `CreateKeyValue` (534), `UpdateKeyValue` (575), `CreateOrUpdateKeyValue` (596), `KeyValue` (509), `DeleteKeyValue` (734).

[source] Create-if-absent: `Create` at `jetstream/kv.go:1062-1090` publishes with an expected last sequence per subject of 0, retries once against the last revision if the key is currently a delete or purge marker, and maps the server's wrong-last-sequence error codes 10071 and 10164 to `ErrKeyExists` (`jetstream/errors.go:385-393`). Compare-and-set: `Update` at 1118 calls `updateRevision`, which sets `WithExpectLastSequencePerSubject(revision)` (1140), so the server rejects the write when the latest revision differs. [adr] ADR-8 lines 122-126 specify exactly these semantics.

[source] `KeyValueConfig` in `jetstream/kv.go`: `History uint8` (228), maximum `KeyValueMaxHistory = 64` (494, enforced at 624-626); `TTL time.Duration` (231) becomes stream `MaxAge` (677); `MaxValueSize` (224); `LimitMarkerTTL time.Duration` (269-273). The bucket stream is created with `MaxMsgsPerSubject = history`, `AllowRollup`, `DenyDelete`, `AllowDirect`, `DiscardNew` (675-690). [adr] ADR-8 lines 240-250 record the same mapping and the 64 history limit.

[source] Per-key TTL: `KeyTTL(ttl) KVCreateOpt` at `jetstream/kv_options.go:123-131` (nats.go v1.42.0, git). Its comment states the TTL is set at creation and cannot be changed later, and requires `LimitMarkerTTL` on the bucket. `Update` passes a zero TTL (1119), and there is no TTL option on `Put`. `PurgeTTL(ttl) KVDeleteOpt` at 105-115 sets a TTL on the purge marker. Setting `LimitMarkerTTL` makes the client check `AccountInfo().API.Level >= 1` and otherwise return `ErrLimitMarkerTTLNotSupported` (659-670, `jetstream/errors.go:447`); when accepted it sets `AllowMsgTTL = true` and `SubjectDeleteMarkerTTL` on the stream (691). Publishing the TTL uses the `Nats-TTL` header (`jetstream/message.go:210`, `jetstream/publish.go:224`).

[source] Server side: `AllowMsgTTL` (json `allow_msg_ttl`) at `server/stream.go:105-107` and `SubjectDeleteMarkerTTL` (json `subject_delete_marker_ttl`) at 109-111, header constants `Nats-TTL` and `Nats-Marker-Reason` at 750-751. `SubjectDeleteMarkerTTL` must be at least one second and implies `AllowMsgTTL` (2050-2058). Both fields first shipped in v2.11.0 (git, commits d517d30d and c8b7c48f).

[adr] ADR-43 (tag 2.11): `Nats-TTL` accepts seconds or a Go duration, minimum 1 second, `never` exempts the message from `MaxAge` (lines 26-33); publishing with the header to a stream with the feature off fails with error 10166 (118); markers carry `Nats-Marker-Reason` of `MaxAge`, `Remove`, or `Purge` (42-75); unless `MaxMsgsPer` is 1, the server raises any `Nats-TTL` below `SubjectDeleteMarkerTTL` up to that floor and rewrites the header (110). ADR-48 (tag 2.11) is the KV refinement, and ADR-8's release history row 7 (2025-01-23) lists the server requirement as 2.11.0.

## 7. Accounts, per-user permissions, templates, per-account JetStream limits

Verdict: partially true. Account isolation and per-user allow and deny lists with wildcards hold. The `{{name()}}` style templates exist only for JWT users signed by a scoped signing key and for auth-callout-issued users. Static users in a server config file get no template expansion, so a config-mode allow list has to spell out the literal subject per user.

[source] `server/accounts.go:49-50`: "Account are subject namespace definitions. By default no messages are shared between accounts. You can share via Exports and Imports of Streams and Services."

[source] Config shape: `accounts { <name> { users [...], jetstream {...}, limits {...}, default_permissions {...}, imports, exports, mappings } }` is parsed at `server/opts.go:3753-3810`. Users are parsed by `parseUsers` (3783-3790) and support `nkey` or user and password plus `permissions` and `allowed_connection_types` (4696-4708). `parseUserPermissions` accepts `publish` (aliases `pub`, `import`), `subscribe` (aliases `sub`, `export`), and `allow_responses` (4861-4875). Each side is a `SubjectPermission{Allow, Deny []string}` (`server/auth.go:130-133`), wrapped in `Permissions{Publish, Subscribe, Response}` (144). Subject wildcards `*` and `>` apply because permission matching uses the server's subject matcher.

[source] Templates: `processUserPermissionsTemplate` at `server/auth.go:479-560` expands `{{name()}}` (the user JWT's name), `{{subject()}}` (the user public nkey), `{{account-name()}}`, `{{account-subject()}}`, `{{tag(key)}}`, and `{{account-tag(key)}}`, using the regex `mustacheRE` at 474. It is called from exactly two places: the JWT path when the issuer is a scoped signing key with a template (`server/auth.go:1037-1049`, `uSc.Template`) and the auth callout path (`server/auth_callout.go:240`). No template processing exists in `server/opts.go`. So a permission such as `agents.{{name()}}.>` works when the user is issued under a scoped signing key or by an auth-callout service, but not for a static config user. The `name()` template first shipped in v2.2.0 (git, commit 74642e02).

[source] Per-account JetStream limits: `JetStreamAccountLimits{MaxMemory, MaxStore, MaxStreams, MaxConsumers, MaxAckPending, MemoryMaxStreamBytes, StoreMaxStreamBytes, MaxBytesRequired}` at `server/jetstream.go:71-78`. Config keys inside an account's `jetstream {}` block are `max_mem`, `max_store` (aliases `max_file`, `max_disk`, `store`, `disk`), `max_streams` (`streams`), `max_consumers` (`consumers`), `max_bytes_required` (`max_stream_bytes`, `max_bytes`), `mem_max_stream_bytes`, `disk_max_stream_bytes`, `max_ack_pending`, `cluster_traffic` (`server/opts.go:2420-2470`). In operator mode the same come from the account JWT's `JetStreamLimits` and tiered limits (`server/accounts.go:3884-3900`). Account connection limits are `limits { max_connections, max_subscriptions, max_payload, max_leafnodes }` (`server/opts.go:3596-3606`).

## 8. Credential types and auth callout

Verdict: true. Auth callout is available from v2.10.0 and receives connection metadata, the presented credentials, and TLS state. It does not receive anything about the client's process.

[source] nats.go options: `UserInfo(user, pass)` at `nats.go:1476`, `Token` at 1494, `Nkey(pubKey, sigCB)` at 1611 and `NkeyOptionFromSeed(seedFile)` at 6808, `UserCredentials(userOrChainedFile, seedFiles...)` at 1519 for `.creds` files, `UserCredentialBytes` at 1538, `UserJWTAndSeed` at 1566, `UserJWT(userCB, sigCB)` at 1589. Server config accepts `nkey` users (`server/opts.go:3141`), and operator mode applies account JWT limits at `server/accounts.go:3852-3855`.

[source] Auth callout: config `authorization { auth_callout { issuer, auth_users, account, xkey, allowed_accounts } }` parsed at `server/opts.go:4627-4834` into `AuthCallout{Issuer, Account, AuthUsers, XKey, AllowedAccounts}` (397-409). It is refused in FIPS-140 mode (4629). The service subject is `AuthCalloutSubject = "$SYS.REQ.USER.AUTH"` (`server/auth_callout.go:30`) and the request header `Nats-Server-Xkey` (32) carries the server's public xkey when encryption is on. The file was added by commit 2daf9049, first released in v2.10.0 (git). [docs] https://docs.nats.io/running-a-nats-service/configuration/securing_nats/auth_callout states "Auth callout requires NATS Server 2.10.0 or later" and that the `account` key defaults to `$G`.

[source] What the callout receives: `fillClientInfo` at `server/auth_callout.go:456-471` populates `Host` (remote IP), `ID` (client id), `User` (raw auth user string), `Name` (client connect name), `Tags`, `NameTag`, `Kind`, `Type` (nats, websocket, mqtt, leafnode), `MQTT` client id, and, when a nonce was signed, `Nonce` (379-380). `fillConnectOpts` at 477-501 copies the CONNECT options: `JWT`, `Nkey`, `SignedNonce`, `Token`, `Username`, `Password`, `Name`, `Lang`, `Version`, `Protocol`. TLS state, when the handshake completed, adds `ClientTLS{Version, Cipher, VerifiedChains}` with the verified chains as PEM (383-400). [adr] ADR-26 lines 105-160 show the request JWT with `client_info`, `client_opts`, `user_nkey`, `server_id`; lines 180-200 show `client_tls`. There is no process id, executable, or host user field anywhere in these structures, which confirms the sketch's assumption.

Caveat: [docs] the callout page warns that `connect_opts` carries the token and password in plaintext inside the request JWT unless `xkey` encryption is configured.

## 9. Leaf nodes and JetStream domains

Verdict: true, with one important nuance. A leaf that has its own JetStream must set a JetStream domain distinct from the hub, otherwise, if the system account is shared, it extends the hub's JetStream instead of running its own. The hub can address the leaf's JetStream through the domain-prefixed API and can mirror or source across the link, but the leaf's streams do not appear in the hub's own JetStream metadata.

[source] Leaf configuration types: `LeafNodeOpts` at `server/opts.go:183` and `RemoteLeafOpts` at 255-268 with `LocalAccount`, `URLs`, `Credentials`, `TLSConfig`, `Hub`, `DenyImports`, `DenyExports`, plus `JetStreamClusterMigrate` (313). Domain is `Options.JetStreamDomain` (469) or `JetStreamConfig.Domain` (`server/jetstream.go:49`), first shipped in v2.2.3 (git, commit 84993765).

[source] The decision logic is in `server/leafnode.go:2035-2087`. If the local and remote domains differ, or the system account is not shared, or JetStream is disabled on one side, the leaf connection gets deny permissions for `$JS.API.>`, `$KV.>`, `$OBJ.>` (`denyAllClientJs`, `server/jetstream_api.go:371`) or additionally the cluster and raft subjects for the system account (`denyAllJs`, 372), and logs "JetStream using domains: local %q, remote %q" (2085). If the domains match and the system account is shared, the leaf extends the hub's JetStream and places its meta controller in observer mode (2088-2096). [docs] https://docs.nats.io/running-a-nats-service/configuration/leafnodes/jetstream_leafnodes says the same: "a leaf and its hub don't automatically get separate JetStream systems. If `factory-1` enables JetStream while sharing the hub's system account, it extends the hub's JetStream rather than running its own."

[source] Cross-domain access: when the leaf has a domain and JetStream enabled, it installs subject mappings from `$JS.<domain>.API.>` to `$JS.API.>` (and the `$KV` and `$OBJ` equivalents) into each non-system account (`server/leafnode.go:2116-2124`, table built by `generateJSMappingTable` at `server/jetstream_api.go:374-388`, format `jsDomainAPI = "$JS.%s.API.>"` at 44). A hub-side client in the same account can therefore talk to the leaf's JetStream with `jetstream.NewWithDomain(nc, domain)` (`nats.go/jetstream/jetstream.go:557`) or `NewWithAPIPrefix` (518). [adr] ADR-19 lines 26-33 and 46 describe the deny of `$JS.API.>` across the leaf link and the automatic prefix-stripping mapping; lines 61-63 cover KV under a domain prefix. Streams on the hub can also mirror or source a leaf stream by setting `StreamSource.External{APIPrefix (json api), DeliverPrefix (json deliver)}` (`nats.go/jetstream/stream_config.go:483,512-515`).

[docs] The 2.15 upgrade guide lists "Domain-prefixed JS API in system account" for managing JetStream domains across leafnodes (https://docs.nats.io/release-notes/upgrade-to-2.15).

Caveat: the embedded server and the hub must both share the same account name for the leaf link (`LocalAccount` on the remote), and the hub must export what the leaf imports if they are in different accounts. If the system account is not shared and no domain is set, the JetStream APIs are denied across the link and the two JetStreams are isolated but the hub cannot address the leaf's.

## 10. TLS on client connections and Unix domain sockets

Verdict: true on both counts. TLS is supported; a Unix domain socket listener does not exist.

[source] Server-side TLS fields on `Options`: `TLSTimeout` (503), `TLSVerify`, `TLSMap`, `TLSCert`, `TLSKey`, `TLSCaCert`, `TLSConfig *tls.Config` (505-510), `TLSPinnedCerts`, `TLSRateLimit` (511-512), `TLSHandshakeFirst` and `TLSHandshakeFirstFallback` (518-524), `AllowNonTLS` (525), all in `server/opts.go`. Config keys in the `tls {}` block: `cert_file`, `key_file`, `ca_file`, `insecure`, `verify`, `verify_and_map`, `verify_cert_and_check_known_urls`, `cipher_suites`, `curve_preferences`, `timeout` (`server/opts.go:5144-5232`). `NewServer` derives the require-client-cert flag from `TLSConfig.ClientAuth == tls.RequireAndVerifyClientCert` (`server/server.go:711-713`).

[source] Client side: `nats.Secure(tlsConfig...)` at `nats.go:1150`, `ClientTLSConfig` at 1169, `RootCAs(files...)` at 1200, `ClientCert(certFile, keyFile)` at 1230, `TLSHandshakeFirst()` at 1763.

[source] Listeners: the client accept loop uses `natsListen("tcp", hp)` at `server/server.go:2879` and `net.Listen("tcp", hp)` at 2968; the monitoring, websocket, MQTT, route, leaf, and gateway listeners are all `"tcp"` as well (`server/server.go:3129,3137`, `server/websocket.go:1304`, `server/mqtt.go:559`, `server/route.go:2753`, `server/leafnode.go:999`, `server/gateway.go:506`). `natsListen` at `server/util.go:273-275` just forwards the network string. No file under `server/` other than tests references the `"unix"` network. The in-process connection from item 1 is the supported alternative to a socket file.

## 11. Ordered consumers and consumer info counters

Verdict: true. An ordered consumer is an ephemeral consumer with its own cursor, so it never touches another consumer's delivered or ack state, and `ConsumerInfo` exposes `NumPending` and `NumAckPending`.

[source] nats.go: `OrderedConsumer(ctx, stream, cfg OrderedConsumerConfig)` at `jetstream/jetstream.go:902` and on a stream handle at `jetstream/stream.go:386`; methods `Consume`, `Messages`, `Fetch`, `FetchBytes`, `FetchNoWait`, `Next`, `Info`, `CachedInfo` at `jetstream/ordered.go:82-739`. The underlying consumer it creates has `AckPolicy: AckNonePolicy`, `InactiveThreshold: 5 * time.Minute`, `Replicas: 1`, `MemoryStorage: true`, and no durable name (`jetstream/ordered.go:631-645`); on a sequence gap it recreates the consumer from the last known stream sequence (`DeliverByStartSequencePolicy`, 616-633). It accepts `FilterSubjects` (641-644).

[adr] ADR-17 "Ordered Consumer" specifies gap detection and recreation from the last good stream sequence (lines 15-24) and the forced settings: no durable name, ack policy none, max deliver 1, flow control, memory storage, one replica (36-53). ADR-17 also says the ordered consumer cannot be a pull consumer; that predates the simplified API in ADR-37, and the nats.go `jetstream` package implements it over pull requests, so treat ADR-17's push-only rule as historical.

[source] `ConsumerInfo` in `server/consumer.go:57-70` has `NumAckPending int` (json `num_ack_pending`), `NumRedelivered`, `NumWaiting` (active pull requests), `NumPending uint64` (json `num_pending`, messages matching the filter not yet delivered), plus `Delivered` and `AckFloor` sequence pairs. The nats.go mirror with field comments is `jetstream/consumer_config.go:49-65`.

## 12. Limits

Verdict: partially true. Max payload defaults to 1 MiB and is configurable. Per-account storage, stream, and consumer limits exist. Connection-count limits exist per server and per account, and there is no per-user connection-count limit in the server's config parser.

[source] `MAX_PAYLOAD_SIZE = (1024 * 1024)` at `server/const.go:92-94`, applied when `Options.MaxPayload` is zero at `server/opts.go:6137-6138`; the config key is `max_payload` (1354). Per-client outbound buffer `MAX_PENDING_SIZE = 64 MiB` at `server/const.go:101-102`. An account can lower payload with `limits { max_payload }` (`server/opts.go:3603`).

[source] Per-account JetStream limits are in item 7 (`server/jetstream.go:71-78`, `server/opts.go:2420-2463`). Server-wide JetStream limits are `jetstream { limits { max_ack_pending, max_ha_assets, max_request_batch, default_max_consumers, duplicate_window, batch {...} } }` (`server/opts.go:2545-2560`) with `JSDefaultMaxConsumersPerStream = 1_000` (`server/jetstream_api.go:418`) applied when unset (`server/opts.go:6204-6205`). Server-wide `Options.JetStreamMaxMemory` and `JetStreamMaxStore` (467-468) cap all accounts together.

[source] Connection limits: server-wide `max_connections` (`server/opts.go:1365-1367`, field `MaxConn` at 435, zero means unlimited); per-account `limits { max_connections, max_leafnodes }` (`server/opts.go:3599-3606`), enforced in `server/accounts.go:514-535`; in operator mode from the account JWT's `Limits.Conn` and `Limits.LeafNodeConn` (`server/accounts.go:3854-3855`). Per-user, `parseUsers` accepts credentials, `permissions`, and `allowed_connection_types` (`server/opts.go:4696-4708`) but no connection count. NOT FOUND: any per-user connection-count limit in `server/opts.go` or `server/auth.go`. The `nats-io/jwt/v2` module source was not on disk (not in the module cache), so the JWT user-limit field list could not be read directly; the server only reads account-level `Conn` for connection counting.

## 13. Current release and changes in 2.11 through 2.15

[source] `git tag` in the server repo: newest stable tags are v2.15.0, then v2.14.7, v2.12.15, v2.11.17. There are no 2.13 tags. `git log -1 v2.15.0` shows the release commit dated 2026-09-17. `RELEASES.md` lines 3-9 state the 6-month minor cadence, that the current and previous minor receive fixes, and that previews ship once feature development completes.

[docs] https://docs.nats.io/release-notes lists 2.15 released 2026-09-17 (latest), 2.14 released 2026-04-30 (maintained), 2.13 "Skipped, never released", 2.12 released 2025-09-22 (end of life, final v2.12.15 on 2026-08-12), 2.11 released 2025-03-19 (end of life, final v2.11.17 on 2026-04-27).

Changes relevant to the assumptions above, by minor version.

2.11 [adr] index section "2.11": ADR-31 direct get, ADR-41 message path tracing, ADR-42 pull consumer priority groups (`PriorityGroups`, `PriorityPolicy` with `overflow` and `pinned_client`, `PinnedTTL` json `priority_timeout`, `Nats-Pin-Id` header; fields at `server/consumer.go:139-141`, first in v2.11.0 by git), ADR-43 per-message TTL (`Nats-TTL`, `AllowMsgTTL`, `SubjectDeleteMarkerTTL`, `Nats-Marker-Reason`), ADR-44 API levels (level 1 is 2.11, level 2 is 2.12; `$JS.API.INFO` advertises it), ADR-48 KV limit markers. [docs] The 2.11 upgrade guide URL returns 404 and the overview page defers to the GitHub changelog, which was outside the allowed fetch scope, so the 2.11 list rests on the ADR index and source.

2.12 [docs] https://docs.nats.io/release-notes/whats_new/whats_new_212: `AllowAtomicPublish` (atomic batch publish), `AllowMsgCounter` (counter CRDT), `AllowMsgSchedules` (scheduled messages), the `prioritized` priority policy, `server_metadata`, mirror promotion, offline assets on downgrade, strict JetStream API JSON parsing on by default (disable with `jetstream { strict: false }`, parsed at `server/opts.go:2699`), `isolate_leafnode_interest`, and `disabled: true` for leaf remotes. [adr] ADR-49 counters (tag 2.12), ADR-50 batch publish (initial 2.12.0, dedup inside batches from 2.12.1), ADR-51 scheduler (initial 2.12.0). [source] `AllowAtomicPublish`, `AllowMsgCounter`, `AllowMsgSchedules` (`server/stream.go:113-120`) and the `prioritized` policy constant `PriorityPrioritized` all first shipped in v2.12.0 (git).

2.14 [source] `AllowBatchPublish` and `AckFlowControl` first shipped in v2.14.0 (git, commits 55056349 and 615f705a). [docs] https://docs.nats.io/release-notes/upgrade-to-2.14: `AllowBatchPublish` fast-ingest batching (ADR-50 revisions 5 to 10, API level 4), recurring and cron schedules plus subject sampling and `Nats-Schedule-Rollup` (ADR-51 revisions 3 to 7), reliable sourcing and mirroring of work-queue and interest streams with the new `AckFlowControl` ack policy (ADR-60), a consumer reset API, leaf remote config reload, `feature_flags` config (ADR-53) including `js_ack_fc_v2` for domain-aware ack subjects, filestore I/O error handling, raft overrun protection. Downgrade note: consumers using `AckFlowControl` go offline on 2.12.

2.15 [docs] https://docs.nats.io/release-notes/upgrade-to-2.15: desired-state metalayer (ADR-62), evacuate endpoints, meta group quorum rescue (ADR-61), domain-prefixed JS API in the system account for managing domains across leafnodes, stream backup and restore v2 (ADR-63), cancel stream move, source stream recreation detection and source indexing, a default per-stream consumer limit of 1000 via `default_max_consumers` and a new `max_consumers` stream and account setting, `js_raft_delete_range` on by default, `request_isolation` leaf isolation across cluster nodes. Downgrade only to v2.14.7 or later and remove `default_max_consumers` first.

Effect on the earlier answers: the 1000-consumer default per stream (item 12) is new in 2.15; `AckFlowControl` (item 3) is new in 2.14 and is not something a normal consumer should select; batch publish (`AllowAtomicPublish` 2.12, `AllowBatchPublish` 2.14) and schedules (`AllowMsgSchedules` 2.12, recurring in 2.14) are opt-in stream flags that do not change dedup, ack, or KV behaviour unless enabled; per-message TTL and KV limit markers (item 6) require 2.11 or later; priority groups and pinned clients (2.11, `prioritized` in 2.12) are an optional pull-request field `group` and do not alter default pull behaviour.

## Gaps

- The `nats-io/jwt/v2` source was not on disk, so JWT `UserLimits` and `UserPermissionLimits` field names are cited only through the server's use of them and ADR-26.
- The 2.11 release notes were not readable within the allowed sources beyond the ADR index; the version claims for 2.11 features rest on ADR tags and git tag containment.
- Git tag containment is by first stable tag containing the introducing commit. Features that landed in a release candidate or preview are reported under the final release (for example `PriorityGroups` is in v2.11.0-RC.1 and reported as v2.11.0).
