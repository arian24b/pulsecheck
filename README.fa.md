<div dir="rtl" align="right">

# pulsecheck

[English](README.md) · **فارسی**

مانیتور آپتایم خودمیزبان. آدرس‌های HTTP(S)، پورت‌های TCP و میزبان‌ها (ping) را در بازه‌های مشخص بررسی می‌کند، وضعیت up / down / کند را نگه می‌دارد و هشدارها را با [shoutrrr](https://github.com/nicholas-fedor/shoutrrr) می‌فرستد (اسلک، تلگرام، دیسکورد، ایمیل، ntfy و بیشتر). یک فایل YAML، یک فایل وضعیت SQLite، بدون داشبورد و بدون تاریخچه گیت.

## امکانات
- بررسی HTTP با متد، هدر، بدنه، کدهای وضعیت مورد انتظار، حد ریدایرکت، حداکثر زمان پاسخ و آستانه «کند» (degraded)
- بررسی TCP و ping
- جایگزینی `${ENV}` تا رمزها بیرون از فایل تنظیم بمانند
- هشدار فقط هنگام تغییر وضعیت، و `down_after` برای نادیده‌گرفتن قطعی‌های کوتاه
- بازه بررسی جدا برای هر سایت، مسیر هشدار جدا برای هر سایت، بازه نگهداری (maintenance) به وقت UTC
- گزارش درصد آپتایم و زمان پاسخ (`report` و `--json`)
- اجرا با GitHub Actions، GitLab CI یا cron
- پایتون ۳٫۱۲ تا ۳٫۱۵ (ترجیحاً ۳٫۱۵) با [uv](https://docs.astral.sh/uv/)

## نصب روی لینوکس (یک دستور)
```bash
curl -fsSL https://raw.githubusercontent.com/arian24b/pulsecheck/main/install.sh | bash
```
بعد `~/.config/pulsecheck/pulsecheck.yml` را ویرایش کنید و `pulsecheck -c ~/.config/pulsecheck/pulsecheck.yml validate` را اجرا کنید.

## شروع سریع (از یک clone)
```bash
uv sync
cp pulsecheck.example.yml pulsecheck.yml     # ویرایشش کنید
uv run pulsecheck validate
uv run pulsecheck test-notify
uv run pulsecheck run [--force] [--fail-on-down]
uv run pulsecheck report [--json]
```
shoutrrr وقتی Docker کار کند از image داکرش اجرا می‌شود، وگرنه از فایل اجرایی `shoutrrr` در `PATH` (با `shoutrrr_bin` در تنظیمات قابل تغییر است). برای `type: ping` دستور `ping` لازم است.

در گیت‌هاب با **Use this template** کپی خودتان را بسازید؛ workflow مربوط به GitHub Actions آماده است. برای GitLab فایل `.gitlab-ci.yml` و برای cron فایل `deploy/cron.example` را استفاده کنید.

## مستندات
| | English | فارسی |
|---|---|---|
| معرفی | [Home](docs/en/Home.md) | [خانه](docs/fa/Home.md) |
| نصب و اولین اجرا | [Getting started](docs/en/Getting-Started.md) | [شروع سریع](docs/fa/Getting-Started.md) |
| همه تنظیمات | [Configuration](docs/en/Configuration.md) | [تنظیمات](docs/fa/Configuration.md) |
| سرویس‌های هشدار | [Notifications](docs/en/Notifications.md) | [اعلان‌ها](docs/fa/Notifications.md) |
| GitHub / GitLab / cron | [Scheduling](docs/en/Scheduling.md) | [زمان‌بندی](docs/fa/Scheduling.md) |
| مشکلات | [Troubleshooting](docs/en/Troubleshooting.md) | [عیب‌یابی](docs/fa/Troubleshooting.md) |

همین مستندات در [ویکی گیت‌هاب](https://github.com/arian24b/pulsecheck/wiki) هم هست (انگلیسی و فارسی؛ `deploy/sync-wiki.sh` آن را از `docs/` به‌روز می‌کند).

## توسعه
```bash
uv run pytest
```

## مجوز
MIT

</div>
