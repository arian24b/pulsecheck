<div dir="rtl" align="right">

# زمان‌بندی

**زبان:** [English](../en/Scheduling.md) · فارسی

pulsecheck یک‌بار اجرا می‌شود و تمام می‌شود. چیز دیگری باید هر چند دقیقه آن را اجرا کند. یکی از روش‌ها را انتخاب کنید.

## GitHub Actions
1. در مخزن روی **Use this template** بزنید (کپی **خصوصی** بهتر است، چون `pulsecheck.yml` شما میزبان‌هایتان را فهرست می‌کند).
2. `pulsecheck.example.yml` را به `pulsecheck.yml` کپی کنید، ویرایش و کامیت کنید. توکن‌ها را به شکل `${VAR}` نگه دارید.
3. هر متغیر را به‌عنوان secret اضافه کنید (Settings ← Secrets and variables ← Actions) و در بخش `env:` مرحله **Run checks** فایل `.github/workflows/monitor.yml` بنویسید. قالب از قبل `TG_TOKEN`، `TG_CHAT` و `API_TOKEN` را دارد.
4. اختیاری: `SHOUTRRR_VERSION` را عوض کنید. یک‌بار با **Actions ← monitor ← Run workflow** اجرا کنید.

نکته‌ها
- workflow داخل خود مخزن قالب اجرا نمی‌شود (`github.repository != 'arian24b/pulsecheck'`). اگر نام کپی خود را عوض کنید همچنان کار می‌کند.
- وضعیت با `actions/cache` ذخیره می‌شود (جدیدترین مورد بازیابی و بعد از هر اجرا ذخیره می‌شود). کامیتی انجام نمی‌شود.
- گیت‌هاب ممکن است اجرای زمان‌بندی‌شده را چند دقیقه به تأخیر بیندازد و زمان‌بندی مخزن‌های بی‌فعالیت را بعد از ۶۰ روز غیرفعال می‌کند.

## GitLab CI
1. مخزن را در GitLab بگذارید و `pulsecheck.yml` خود را کامیت کنید.
2. **Build ← Pipeline schedules ← New schedule** با cron برابر `*/5 * * * *`.
3. **Settings ← CI/CD ← Variables**: همه `${VAR}`هایی که فایل استفاده می‌کند را اضافه کنید (رمزها را mask کنید).
4. job فقط برای pipelineهای زمان‌بندی‌شده اجرا می‌شود و `pulsecheck.db` را با یک کلید در cache نگه می‌دارد. اگر runnerهای شما cache مشترک ندارند وضعیت بین اجراها از بین می‌رود (بخش [عیب‌یابی](Troubleshooting.md)).

## کرون لینوکس
```bash
# crontab -e
*/5 * * * * cd /opt/pulsecheck && TG_TOKEN=xxx TG_CHAT=@mychannel API_TOKEN=xxx flock -n /tmp/pulsecheck.lock uv run pulsecheck -c pulsecheck.yml run >> /var/log/pulsecheck.log 2>&1
```
وضعیت در `state_file` روی دیسک می‌ماند. `flock -n` از هم‌پوشانی اجراها جلوگیری می‌کند. برای رمزها به‌جای نوشتن در crontab از یک فایل env و یک اسکریپت کوچک استفاده کنید.

</div>
