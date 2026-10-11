<div dir="rtl" align="right">

# pulsecheck

[English](https://github.com/arian24b/pulsecheck/blob/main/README.md) · **فارسی**

pulsecheck یک مانیتور آپتایم است که خودتان میزبانی‌اش می‌کنید. در بازه‌هایی که تعیین می‌کنید آدرس‌های HTTP(S)، پورت‌های TCP و سرورها (با ping) را بررسی می‌کند، وضعیت up، down و کند را نگه می‌دارد و با [shoutrrr](https://github.com/nicholas-fedor/shoutrrr) خبر می‌دهد: اسلک، تلگرام، دیسکورد، ایمیل، ntfy و بیش از ۲۰ سرویس دیگر. یک فایل YAML و یک فایل وضعیت دارد؛ داشبورد و تاریخچه‌ی گیت ندارد.

## امکانات
- بررسی HTTP با متد، هدر، بدنه، کدهای مورد انتظار، حد ریدایرکت، حداکثر زمان پاسخ و آستانه‌ی «کند» (degraded)
- هشدار نزدیک شدن انقضای گواهی TLS (`ssl_warn_days`) و شکست بررسی در صورت منقضی بودن گواهی
- بررسی TCP و ping
- هشدار فقط هنگام تغییر وضعیت؛ `down_after` برای نادیده گرفتن قطع‌های کوتاه و `remind_every` برای یادآوری تکراری
- متن هشدارها بر اساس کلید قابل ویرایش است (`messages:`، سراسری یا برای هر سایت)
- برچسب، بازه‌ی بررسی و مسیر هشدار جدا برای هر سایت؛ بازه‌ی نگهداری (maintenance) به وقت UTC
- دستور `status` (متن، JSON، مارک‌دان) و `report` (درصد آپتایم و زمان پاسخ) بدون داشبورد
- ارسال OpenTelemetry (متریک و لاگ OTLP/HTTP JSON) به هر collector یا وب‌هوک
- راه‌اندازی راهنمادار: `init` (تنظیمات، `.env`، shoutrrr و cron)، `env`، `validate`، `test-notify` برای همه‌ی کانال‌ها و `update`
- جایگزینی `${ENV}` تا رمزها بیرون از فایل تنظیم بمانند
- اجرا با GitHub Actions، GitLab CI یا cron، یا سرورلس روی Vercel و Cloudflare Workers (با [محدودیت‌هایش](https://github.com/arian24b/pulsecheck/wiki/FA-Serverless))
- پایتون ۳٫۱۲ تا ۳٫۱۵ (۳٫۱۵ ترجیح دارد) با [uv](https://docs.astral.sh/uv/)

## نصب
بسته‌ی PyPI اسمش `pulsecheckcli` است، اما دستورش `pulsecheck` (و اسم کوتاه‌تر `pck`) است.
```bash
uv tool install pulsecheckcli     # یا: pipx install pulsecheckcli
pulsecheck init                   # تنظیمات، .env، shoutrrr و cron job (لینوکس)
pulsecheck env                    # توکن‌ها را اضافه کنید
pulsecheck validate && pulsecheck test-notify
```
همه‌ی دستورها در [دستورها](https://github.com/arian24b/pulsecheck/wiki/FA-Commands) آمده است.

### یا با یک خط از گیت‌هاب (لینوکس)
```bash
curl -fsSL https://raw.githubusercontent.com/arian24b/pulsecheck/main/install.sh | bash
```
این خط بسته‌ی `pulsecheckcli` را با `uv tool` نصب می‌کند و `pulsecheck init` را اجرا می‌کند. بعد `pulsecheck env`، `pulsecheck validate` و `pulsecheck test-notify` را بزنید.

## شروع سریع (از روی clone)
```bash
uv sync
cp pulsecheck.example.yml pulsecheck.yml     # ویرایشش کنید
uv run pulsecheck validate
uv run pulsecheck test-notify
uv run pulsecheck run [--force] [--fail-on-down] [--tag prod]
uv run pulsecheck status [--json|--md]
uv run pulsecheck report [--json]
```
اگر Docker کار کند shoutrrr از image داکرش اجرا می‌شود، وگرنه از فایل اجرایی `shoutrrr` در `PATH` (با `shoutrrr_bin` در تنظیمات می‌توانید این را عوض کنید). برای `type: ping` به دستور `ping` نیاز دارید.

اگر می‌خواهید با کمترین فایل روی GitHub Actions اجرایش کنید، در [pulsecheck-template](https://github.com/arian24b/pulsecheck-template) روی **Use this template** بزنید: فقط `pulsecheck.yml`، یک workflow و یک README کوتاه می‌گیرید. **کپی خودتان را خصوصی نگه دارید**، چون `pulsecheck.yml` نام سرورهای شما را در خود دارد.

## مستندات (ویکی)
| | English | فارسی |
|---|---|---|
| معرفی | [Home](https://github.com/arian24b/pulsecheck/wiki/Home) | [خانه](https://github.com/arian24b/pulsecheck/wiki/FA-Home) |
| همه‌ی دستورها | [Commands](https://github.com/arian24b/pulsecheck/wiki/Commands) | [دستورها](https://github.com/arian24b/pulsecheck/wiki/FA-Commands) |
| نصب و اولین اجرا | [Getting started](https://github.com/arian24b/pulsecheck/wiki/Getting-Started) | [شروع سریع](https://github.com/arian24b/pulsecheck/wiki/FA-Getting-Started) |
| هر کلید YAML (نوع و پیش‌فرض) | [YAML reference](https://github.com/arian24b/pulsecheck/wiki/YAML-Reference) | [مرجع YAML](https://github.com/arian24b/pulsecheck/wiki/FA-YAML-Reference) |
| توضیح تنظیمات | [Configuration](https://github.com/arian24b/pulsecheck/wiki/Configuration) | [تنظیمات](https://github.com/arian24b/pulsecheck/wiki/FA-Configuration) |
| سرویس‌های هشدار | [Notifications](https://github.com/arian24b/pulsecheck/wiki/Notifications) | [اعلان‌ها](https://github.com/arian24b/pulsecheck/wiki/FA-Notifications) |
| GitHub، GitLab و cron | [Scheduling](https://github.com/arian24b/pulsecheck/wiki/Scheduling) | [زمان‌بندی](https://github.com/arian24b/pulsecheck/wiki/FA-Scheduling) |
| Vercel و Cloudflare | [Serverless](https://github.com/arian24b/pulsecheck/wiki/Serverless) | [سرورلس](https://github.com/arian24b/pulsecheck/wiki/FA-Serverless) |
| ساختار برنامه و آنچه تست شده | [Design notes](https://github.com/arian24b/pulsecheck/wiki/Design-Notes) | [یادداشت‌های طراحی](https://github.com/arian24b/pulsecheck/wiki/FA-Design-Notes) |
| مشکل‌های رایج | [Troubleshooting](https://github.com/arian24b/pulsecheck/wiki/Troubleshooting) | [عیب‌یابی](https://github.com/arian24b/pulsecheck/wiki/FA-Troubleshooting) |

همین مستندات در [ویکی گیت‌هاب](https://github.com/arian24b/pulsecheck/wiki) هم هست، به دو زبان انگلیسی و فارسی. پرسش و پاسخ: [Discussions](https://github.com/arian24b/pulsecheck/discussions). مشارکت: [CONTRIBUTING](https://github.com/arian24b/pulsecheck/blob/main/.github/CONTRIBUTING.md). امنیت: [SECURITY](https://github.com/arian24b/pulsecheck/blob/main/.github/SECURITY.md).

## توسعه
```bash
uv run pytest -q && uv run ruff check . && uv run ruff format --check .
```
پیام commitها باید از Conventional Commits پیروی کنند (`feat:`، `fix:` و …)، چون نسخه، CHANGELOG و انتشار در PyPI از روی آن‌ها خودکار ساخته می‌شود.

## مجوز
MIT

</div>
