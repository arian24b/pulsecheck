<div dir="rtl" align="right">

# pulsecheck

[English](https://github.com/arian24b/pulsecheck/blob/main/README.md) · **فارسی**

مانیتور آپتایم خودمیزبان. آدرس‌های HTTP(S)، پورت‌های TCP و میزبان‌ها (ping) را در بازه‌های مشخص بررسی می‌کند، وضعیت up / down / کند را نگه می‌دارد و هشدارها را با [shoutrrr](https://github.com/nicholas-fedor/shoutrrr) می‌فرستد (اسلک، تلگرام، دیسکورد، ایمیل، ntfy و بیش از ۲۰ سرویس دیگر). یک فایل YAML، یک فایل وضعیت، بدون داشبورد و بدون تاریخچه گیت.

## امکانات
- بررسی HTTP: متد، هدر، بدنه، کد وضعیت مورد انتظار، حد ریدایرکت، حداکثر زمان پاسخ و آستانه «کند» (degraded)
- هشدار انقضای گواهی TLS (`ssl_warn_days`) و شکست در صورت منقضی‌بودن گواهی
- بررسی TCP و ping
- هشدار فقط هنگام تغییر وضعیت، `down_after` برای نادیده‌گرفتن قطعی‌های کوتاه و یادآوری تکراری اختیاری (`remind_every`)
- برچسب (tag)، بازه بررسی و مسیر هشدار جدا برای هر سایت؛ بازه نگهداری (maintenance) به وقت UTC
- متن هشدارها بر اساس کلید قابل ویرایش است (`messages:`)
- دستور `status` (متن، JSON، مارک‌دان) و `report` (درصد آپتایم، زمان پاسخ) بدون داشبورد
- ارسال OpenTelemetry (متریک و لاگ OTLP/HTTP JSON) به هر collector یا وب‌هوک
- راه‌اندازی هدایت‌شده: `init` (تنظیمات، `.env`، shoutrrr، cron)، `env`، `validate`، `test-notify` برای همه کانال‌ها و `update`
- جایگزینی `${ENV}` تا رمزها بیرون از فایل تنظیم بمانند
- اجرا با GitHub Actions، GitLab CI، cron یا سرورلس روی Vercel و Cloudflare Workers (با [محدودیت‌ها](https://github.com/arian24b/pulsecheck/wiki/FA-Serverless))
- پایتون ۳٫۱۲ تا ۳٫۱۵ (ترجیحاً ۳٫۱۵) با [uv](https://docs.astral.sh/uv/)

## نصب
```bash
uv tool install pulsecheckcli     # یا: pipx install pulsecheckcli   (بعد از اولین انتشار در PyPI)
pulsecheck init                   # تنظیمات + .env + shoutrrr + cron job (لینوکس)
pulsecheck env                    # توکن‌ها را اضافه کنید
pulsecheck validate && pulsecheck test-notify
```
همه دستورها: [دستورها](https://github.com/arian24b/pulsecheck/wiki/FA-Commands).

### یا: یک دستور از گیت‌هاب (لینوکس)
```bash
curl -fsSL https://raw.githubusercontent.com/arian24b/pulsecheck/main/install.sh | bash
```
بسته PyPI با نام `pulsecheckcli` را با `uv tool` نصب می‌کند (تا اولین انتشار از گیت‌هاب) و `pulsecheck init` را اجرا می‌کند. بعد `pulsecheck env`، `pulsecheck validate` و `pulsecheck test-notify` را اجرا کنید.

## شروع سریع (از یک clone)
```bash
uv sync
cp pulsecheck.example.yml pulsecheck.yml     # ویرایشش کنید
uv run pulsecheck validate
uv run pulsecheck test-notify
uv run pulsecheck run [--force] [--fail-on-down] [--tag prod]
uv run pulsecheck status [--json|--md]
uv run pulsecheck report [--json]
```
shoutrrr وقتی Docker کار کند از image داکرش اجرا می‌شود، وگرنه از فایل اجرایی `shoutrrr` در `PATH`. برای `type: ping` دستور `ping` لازم است.

با **Use this template** کپی خودتان را بسازید؛ workflow مربوط به GitHub Actions آماده است. **کپی خودتان را خصوصی نگه دارید**: `pulsecheck.yml` شما نام میزبان‌هایتان را فهرست می‌کند.

## مستندات (ویکی)
| | English | فارسی |
|---|---|---|
| معرفی | [Home](https://github.com/arian24b/pulsecheck/wiki/Home) | [خانه](https://github.com/arian24b/pulsecheck/wiki/FA-Home) |
| همه دستورها | [Commands](https://github.com/arian24b/pulsecheck/wiki/Commands) | [دستورها](https://github.com/arian24b/pulsecheck/wiki/FA-Commands) |
| نصب و اولین اجرا | [Getting started](https://github.com/arian24b/pulsecheck/wiki/Getting-Started) | [شروع سریع](https://github.com/arian24b/pulsecheck/wiki/FA-Getting-Started) |
| هر کلید YAML (نوع، پیش‌فرض) | [YAML reference](https://github.com/arian24b/pulsecheck/wiki/YAML-Reference) | [مرجع YAML](https://github.com/arian24b/pulsecheck/wiki/FA-YAML-Reference) |
| همه تنظیمات، توضیح‌دار | [Configuration](https://github.com/arian24b/pulsecheck/wiki/Configuration) | [تنظیمات](https://github.com/arian24b/pulsecheck/wiki/FA-Configuration) |
| سرویس‌های هشدار | [Notifications](https://github.com/arian24b/pulsecheck/wiki/Notifications) | [اعلان‌ها](https://github.com/arian24b/pulsecheck/wiki/FA-Notifications) |
| GitHub / GitLab / cron | [Scheduling](https://github.com/arian24b/pulsecheck/wiki/Scheduling) | [زمان‌بندی](https://github.com/arian24b/pulsecheck/wiki/FA-Scheduling) |
| Vercel / Cloudflare | [Serverless](https://github.com/arian24b/pulsecheck/wiki/Serverless) | [سرورلس](https://github.com/arian24b/pulsecheck/wiki/FA-Serverless) |
| چگونه کار می‌کند، چه تست شده | [Design notes](https://github.com/arian24b/pulsecheck/wiki/Design-Notes) | [یادداشت‌های طراحی](https://github.com/arian24b/pulsecheck/wiki/FA-Design-Notes) |
| مشکلات | [Troubleshooting](https://github.com/arian24b/pulsecheck/wiki/Troubleshooting) | [عیب‌یابی](https://github.com/arian24b/pulsecheck/wiki/FA-Troubleshooting) |

پرسش و پاسخ: [Discussions](https://github.com/arian24b/pulsecheck/discussions). مشارکت: [CONTRIBUTING](https://github.com/arian24b/pulsecheck/blob/main/.github/CONTRIBUTING.md). امنیت: [SECURITY](https://github.com/arian24b/pulsecheck/blob/main/.github/SECURITY.md).

## توسعه
```bash
uv run pytest -q && uv run ruff check . && uv run ruff format --check .
```

## مجوز
MIT

</div>
