<div dir="rtl" align="right">

# عیب‌یابی

**زبان:** [English](../en/Troubleshooting.md) · فارسی

| مشکل | علت و راه‌حل |
|---|---|
| `config error: env var X is not set` | فایل از `${X}` استفاده می‌کند ولی متغیر export نشده. آن را تنظیم کنید یا secret را به `env:` مرحله CI اضافه کنید. |
| هنگام down بودن سایت هشداری نمی‌آید | سایت باید `down_after` بار پشت‌سرهم شکست بخورد (پیش‌فرض ۲). `events`، فعال‌بودن بازه maintenance (به UTC) و پیام `notify failed` در stderr را بررسی کنید. |
| `notify failed: ... No such file or directory: 'shoutrrr'` | نه Docker قابل‌استفاده است و نه فایل اجرایی در `PATH`. Docker را روشن کنید، فایل اجرایی را نصب کنید (`install.sh` انجام می‌دهد) یا `shoutrrr_bin` را تنظیم کنید. |
| Docker نصب است ولی فایل اجرایی استفاده می‌شود | `docker info` برای کاربر شما شکست می‌خورد (daemon خاموش است یا دسترسی نیست). درستش کنید یا `shoutrrr_bin: docker` بگذارید. |
| `notify failed:` همراه با خطای shoutrrr | آدرس یا توکن اشتباه است. `shoutrrr verify --url ...` و `pulsecheck test-notify` را اجرا کنید. |
| هشدار DOWN مدام تکرار می‌شود | وضعیت بین اجراها از بین رفته (حذف cache، runnerهای بدون cache مشترک، کانتینر بدون volume). `state_file` را روی ذخیره‌سازی پایدار بگذارید. |
| سایت بین up و degraded نوسان می‌کند | `slow_ms` به زمان پاسخ معمول نزدیک است. آن را بالاتر ببرید. |
| ping در Docker/CI همیشه شکست می‌خورد | `iputils-ping` را نصب کنید؛ بعضی کانتینرها raw socket را هم ممنوع می‌کنند. به‌جایش از `type: tcp` استفاده کنید. |
| خطای گواهی HTTPS | بررسی با همان خطا که در هشدار آمده شکست می‌خورد. گواهی را درست کنید؛ گزینه‌ای برای نادیده‌گرفتن اعتبارسنجی نیست. |
| اجرای زمان‌بندی‌شده گیت‌هاب متوقف شد | بعد از ۶۰ روز بی‌فعالیتی مخزن، زمان‌بندی متوقف می‌شود. در تب Actions دوباره فعالش کنید. |
| endpoint در Vercel جواب `401` می‌دهد | `CRON_SECRET` تنظیم نشده یا هدر `Authorization: Bearer …` با آن برابر نیست. |
| Vercel جواب `500 … state store missing` می‌دهد | Upstash Redis را اضافه کنید (`vercel install upstash`) یا `UPSTASH_REDIS_REST_URL` و `UPSTASH_REDIS_REST_TOKEN` را تنظیم کنید. |
| deploy در Vercel روی عبارت cron خطا می‌دهد | Hobby فقط روزی یک اجرا می‌پذیرد. از `0 0 * * *` استفاده کنید یا endpoint را از گیت‌هاب صدا بزنید (بخش [سرورلس](Serverless.md)). |
| `notify failed: 'xyz://' is not supported here` | Vercel/Cloudflare فقط آدرس‌های telegram، discord، ntfy و generic را می‌فرستند. برای سرویس‌های دیگر از حالت دیگری استفاده کنید. |
| `skipped, type 'tcp' is not supported on this platform` | Cloudflare فقط بررسی HTTP دارد؛ Vercel هم `ping` را رد می‌کند. |
| اجرای Cloudflare با «exceeded CPU time» متوقف می‌شود | پلن رایگان برای هر اجرای cron ۱۰ میلی‌ثانیه CPU می‌دهد. پلن پولی را استفاده کنید. |
| خطای نوشتن KV در Cloudflare بعد از چند ساعت | KV رایگان روزی ۱۰۰۰ نوشتن می‌دهد؛ cron یک‌دقیقه‌ای ۱۴۴۰ می‌خواهد. بازه ۲ دقیقه یا بیشتر یا پلن پولی. |

نکته برای اشکال‌زدایی: `uv run pulsecheck run --force` برای هر سایت یک خط با وضعیت، زمان و خطا چاپ می‌کند.

</div>
