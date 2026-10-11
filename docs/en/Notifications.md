# Notifications

**Language:** English · [فارسی](../fa/Notifications.md)

pulsecheck calls `shoutrrr send --url <url> --message <text>` for every URL. How shoutrrr is started is set by `shoutrrr_bin`:

| Value | Behaviour |
|---|---|
| `auto` (default) | `docker run --rm nickfedor/shoutrrr:<version> send …` if Docker works (`docker info` succeeds), otherwise the `shoutrrr` binary on `PATH` |
| `docker` | Always the docker image |
| a path, e.g. `/usr/local/bin/shoutrrr` | Always that binary |

`shoutrrr_image` (default `nickfedor/shoutrrr:0.21.2`) chooses the image; the first send pulls it. Without Docker, install the binary from the [releases page](https://github.com/nicholas-fedor/shoutrrr/releases) (`install.sh` does this for you):

```bash
curl -fsSL https://github.com/nicholas-fedor/shoutrrr/releases/download/v0.21.2/shoutrrr_linux_amd64_0.21.2.tar.gz | sudo tar xz -C /usr/local/bin shoutrrr
shoutrrr --version
```
Other platforms: pick the matching file (`linux_arm64v8`, `macOS_arm64v8`, …) from the same release.

## URL examples (verified with shoutrrr 0.21.2)
| Service | URL |
|---|---|
| Telegram | `telegram://BOT_TOKEN@telegram?chats=@channel` (or a numeric chat id) |
| Discord | `discord://TOKEN@WEBHOOK_ID` |
| ntfy | `ntfy://ntfy.sh/your-topic` |
| Email | `smtp://user:pass@mail.example.com:587/?from=a@example.com&to=b@example.com` |
| Slack (bot) | `slack://xoxb:BOT_TOKEN@CHANNEL_ID` |
| Generic webhook | `generic://example.com/hook` |

Many more services exist. Useful commands:
```bash
shoutrrr docs            # list services
shoutrrr docs telegram   # options for one service
shoutrrr verify --url "<url>"   # check a URL without sending
shoutrrr generate telegram      # build a URL interactively
```
**Vercel and Cloudflare Workers** cannot run shoutrrr, so they send alerts with plain HTTPS calls and understand only `telegram://`, `discord://`, `ntfy://` and `generic://` URLs (same format as above; `generic://` accepts `?disabletls=yes` and `?messagekey=`). Other URLs print `notify failed: … not supported here` and nothing is sent. See [Serverless](Serverless.md).

URLs contain secrets: put tokens in environment variables (`${TG_TOKEN}`) or CI secrets, never in the file.

## Routing
```yaml
notify:                      # everything goes here by default
  urls: ["ntfy://ntfy.sh/team-alerts"]
  events: [down, up]
sites:
  - name: payments
    url: https://pay.example.com
    notify:                  # this site only goes to the on-call channel, including degraded
      urls: ["telegram://${TG_TOKEN}@telegram?chats=${ONCALL}"]
      events: [down, up, degraded]
```
Test any change with `uv run pulsecheck test-notify` (it uses the global `notify`).

## Messages
The texts are the built-in defaults and can be changed with `messages:` in the YAML (keys `down`, `degraded`, `up`, `test`). See [Configuration](Configuration.md#messages).
