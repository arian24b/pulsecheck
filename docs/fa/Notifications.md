<div dir="rtl" align="right">

# اعلان‌ها

**زبان:** [English](../en/Notifications.md) · فارسی

pulsecheck برای هر آدرس دستور `shoutrrr send --url <url> --message <text>` را اجرا می‌کند. نحوه اجرای shoutrrr را `shoutrrr_bin` تعیین می‌کند:

| مقدار | رفتار |
|---|---|
| `auto` (پیش‌فرض) | اگر Docker کار کند (`docker info` موفق باشد) `docker run --rm nickfedor/shoutrrr:<version> send …`، وگرنه فایل اجرایی `shoutrrr` در `PATH` |
| `docker` | همیشه image داکر |
| یک مسیر، مثل `/usr/local/bin/shoutrrr` | همیشه همان فایل اجرایی |

`shoutrrr_image` (پیش‌فرض `nickfedor/shoutrrr:0.21.2`) image را مشخص می‌کند؛ اولین ارسال آن را دانلود می‌کند. بدون Docker فایل اجرایی را از [صفحه releases](https://github.com/nicholas-fedor/shoutrrr/releases) نصب کنید (`install.sh` این کار را خودش می‌کند):

```bash
curl -fsSL https://github.com/nicholas-fedor/shoutrrr/releases/download/v0.21.2/shoutrrr_linux_amd64_0.21.2.tar.gz | sudo tar xz -C /usr/local/bin shoutrrr
shoutrrr --version
```
برای سیستم‌های دیگر فایل مناسب (`linux_arm64v8`، `macOS_arm64v8` و …) را از همان release بردارید.

## نمونه آدرس‌ها (با shoutrrr نسخه 0.21.2 بررسی شده)
| سرویس | آدرس |
|---|---|
| تلگرام | `telegram://BOT_TOKEN@telegram?chats=@channel` (یا شناسه عددی چت) |
| دیسکورد | `discord://TOKEN@WEBHOOK_ID` |
| ntfy | `ntfy://ntfy.sh/your-topic` |
| ایمیل | `smtp://user:pass@mail.example.com:587/?from=a@example.com&to=b@example.com` |
| اسلک (بات) | `slack://xoxb:BOT_TOKEN@CHANNEL_ID` |
| وب‌هوک عمومی | `generic://example.com/hook` |

سرویس‌های بسیار بیشتری هست. دستورهای مفید:
```bash
shoutrrr docs            # فهرست سرویس‌ها
shoutrrr docs telegram   # گزینه‌های یک سرویس
shoutrrr verify --url "<url>"   # بررسی آدرس بدون ارسال
shoutrrr generate telegram      # ساخت آدرس به‌صورت تعاملی
```
**Vercel و Cloudflare Workers** نمی‌توانند shoutrrr را اجرا کنند، پس هشدار را با فراخوانی ساده HTTPS می‌فرستند و فقط آدرس‌های `telegram://`، `discord://`، `ntfy://` و `generic://` را می‌شناسند (همان قالب بالا؛ `generic://` گزینه‌های `?disabletls=yes` و `?messagekey=` را می‌پذیرد). آدرس‌های دیگر پیام `notify failed: … not supported here` چاپ می‌کنند و چیزی ارسال نمی‌شود. بخش [سرورلس](Serverless.md) را ببینید.

آدرس‌ها حاوی اطلاعات محرمانه‌اند: توکن‌ها را در متغیر محیطی (`${TG_TOKEN}`) یا secret سیستم CI نگه دارید، نه داخل فایل.

## مسیردهی
```yaml
notify:                      # به‌طور پیش‌فرض همه‌چیز به اینجا می‌رود
  urls: ["ntfy://ntfy.sh/team-alerts"]
  events: [down, up]
sites:
  - name: payments
    url: https://pay.example.com
    notify:                  # این سایت فقط به کانال آنکال می‌رود، با degraded
      urls: ["telegram://${TG_TOKEN}@telegram?chats=${ONCALL}"]
      events: [down, up, degraded]
```
هر تغییری را با `uv run pulsecheck test-notify` امتحان کنید (از `notify` سراسری استفاده می‌کند).

## متن پیام‌ها
متن‌ها پیش‌فرض داخلی‌اند و با `messages:` در YAML قابل تغییرند (کلیدهای `down`، `degraded`، `up`، `test`). بخش [تنظیمات](Configuration.md) را ببینید.

</div>
