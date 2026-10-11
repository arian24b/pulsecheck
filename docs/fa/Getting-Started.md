<div dir="rtl" align="right">

# شروع سریع

**زبان:** [English](../en/Getting-Started.md) · فارسی

## نصب با یک دستور (لینوکس)
```bash
curl -fsSL https://raw.githubusercontent.com/arian24b/pulsecheck/main/install.sh | bash
```
این اسکریپت در صورت نبودن uv آن را نصب می‌کند، کد را در `~/.local/share/pulsecheck` می‌گذارد، دستور `pulsecheck` را در `~/.local/bin` می‌سازد، shoutrrr را آماده می‌کند (image داکر اگر Docker کار کند، وگرنه فایل اجرایی) و فایل `~/.config/pulsecheck/pulsecheck.yml` را می‌سازد. برای به‌روزرسانی دوباره اجرایش کنید. بعد: `pulsecheck -c ~/.config/pulsecheck/pulsecheck.yml validate`. تنظیمات اسکریپت (`PULSECHECK_HOME`، `PULSECHECK_BIN`، `PULSECHECK_CONFIG`، `PULSECHECK_REF`، `SHOUTRRR_VERSION`، `PULSECHECK_SHOUTRRR=binary`) بالای فایل `install.sh` توضیح داده شده است.

## نصب دستی
### پیش‌نیازها
- [uv](https://docs.astral.sh/uv/) (پایتون مناسب را خودش نصب می‌کند؛ پایتون ۳٫۱۲ تا ۳٫۱۵ پشتیبانی می‌شود و ۳٫۱۵ ترجیح داده می‌شود)
- Docker، **یا** فایل اجرایی `shoutrrr` در `PATH` (بخش [اعلان‌ها](Notifications.md))
- دستور `ping` فقط اگر از `type: ping` استفاده می‌کنید (در لینوکس بسته `iputils-ping`)

### گرفتن کد
```bash
git clone https://github.com/arian24b/pulsecheck && cd pulsecheck
# یا در گیت‌هاب روی «Use this template» بزنید تا کپی مخصوص خودتان ساخته شود
uv sync
cp pulsecheck.example.yml pulsecheck.yml
```

## بررسی تنظیمات و هشدار
```bash
export TG_TOKEN=... TG_CHAT=@mychannel API_TOKEN=...   # هر ${متغیری} که در فایل دارید
uv run pulsecheck validate        # فایل را می‌خواند و خطاها را نشان می‌دهد
uv run pulsecheck test-notify     # پیام آزمایشی به آدرس‌های notify سراسری می‌فرستد
```

## اجرا
```bash
uv run pulsecheck run             # همه سایت‌هایی که نوبتشان است را بررسی می‌کند
uv run pulsecheck run --force     # interval هر سایت را نادیده می‌گیرد
uv run pulsecheck run --fail-on-down   # اگر سایتی down باشد کد خروج ۱ می‌دهد (در CI قرمز می‌شود)
uv run pulsecheck report          # درصد آپتایم و زمان پاسخ
uv run pulsecheck report --json
uv run pulsecheck -c other.yml run     # فایل تنظیم دیگر (گزینه -c را قبل از دستور بنویسید)
```
خروجی برای هر سایت یک خط است، مثلاً `web: up 131ms`.

قدم بعد: [زمان‌بندی](Scheduling.md).

</div>
