<div dir="rtl" align="right">

# سرورلس: Vercel و Cloudflare Workers

**زبان:** [English](../en/Serverless.md) · فارسی

علاوه بر GitHub Actions، GitLab CI و cron، pulsecheck روی **Vercel** (cron job و تابع پایتون) و **Cloudflare Workers** (cron trigger و Python Worker) هم اجرا می‌شود. هر دو پلتفرم محیط محدود (sandbox) هستند و بعضی قابلیت‌ها در آن‌ها نیست. اول محدودیت‌ها را بخوانید.

> وضعیت: موتور مشترک، ذخیره‌ساز وضعیت، اعلان HTTP و handler مربوط به Vercel به‌صورت محلی تست شده‌اند (Vercel با یک Redis ساختگی). Worker کلودفلر فقط با جایگزین‌های ساختگی محیط اجرایش تست شده و **هیچ‌کدام از دو پلتفرم با حساب واقعی deploy نشده‌اند**. مشکلات را گزارش کنید.

## چه چیزی کجا کار می‌کند
| قابلیت | CLI / CI / cron | Vercel | Cloudflare Worker |
|---|---|---|---|
| بررسی HTTP | بله | بله | بله (توضیحات پایین) |
| بررسی TCP | بله | بله | **خیر** (رد می‌شود) |
| بررسی ping | بله | **خیر** (رد می‌شود) | **خیر** (رد می‌شود) |
| هشدار | همه سرویس‌های shoutrrr | telegram، discord، ntfy، generic | telegram، discord، ntfy، generic |
| ذخیره وضعیت | فایل SQLite | Upstash Redis (REST) | Workers KV |
| گزارش با p95 | بله | خیر (فقط درصد آپتایم و میانگین؛ ۹۰ روز اخیر) | خیر (همان) |
| `messages:`، maintenance، `down_after`، `interval` | بله | بله | بله |

سایت‌های ردشده در لاگ اجرا فهرست می‌شوند. `max_redirects` در کلودفلر نادیده گرفته می‌شود (fetch با حد خودش ریدایرکت را دنبال می‌کند).

## محدودیت‌های پیداشده در مستندات پلتفرم‌ها
### Vercel
| محدودیت | مقدار | کاری که ما کرده‌ایم |
|---|---|---|
| تناوب cron | Hobby: روزی یک‌بار و در هر لحظه از آن ساعت؛ Pro/Enterprise: هر دقیقه | `vercel.json` با زمان‌بندی **روزانه** می‌آید تا روی هر پلن deploy شود. روی Pro مقدار `*/5 * * * *` را بگذارید. روی Hobby از workflow اختیاری `trigger-vercel.yml` (پایین) استفاده کنید. |
| تحویل cron | تلاش بدون ضمانت: ممکن است اجرا از دست برود یا دوبار شود؛ retry ندارد؛ ریدایرکت دنبال نمی‌شود | اجراها بر پایه تغییر وضعیت‌اند و تکرار بی‌ضرر است. گاهی فاصله ممکن است. |
| تعداد cron در هر پروژه | ۱۰۰ | – |
| نسخه پایتون | ۳٫۱۲ (پیش‌فرض)، ۳٫۱۳، ۳٫۱۴. **۳٫۱۵ نه** | مخزن محلی ۳٫۱۵ را ترجیح می‌دهد؛ اگر build در Vercel `.python-version` را نپذیرفت، در کپی خودتان آن را `3.14` کنید. |
| مدت اجرا | پیش‌فرض ۳۰۰ ثانیه (Hobby حداکثر ۳۰۰، Pro حداکثر ۸۰۰) | برای بررسی‌ها کافی است؛ هر بررسی `timeout` خودش را دارد. |
| حافظه / حجم بسته | ۲ گیگ (Hobby) / ۴ گیگ (Pro)؛ ۵۰۰ مگابایت برای پایتون | `excludeFiles` مستندات و تست‌ها را بیرون نگه می‌دارد. |
| File descriptor | ۱۰۲۴ مشترک بین همه اجراهای هم‌زمان | بررسی‌ها ۲۰ تا ۲۰ تا اجرا می‌شوند. |
| دیسک محلی | جای مناسبی برای وضعیت نیست | وضعیت در Upstash Redis است. |
| Docker / فایل اجرایی اضافه | برای توابع پایتون در دسترس نیست | به‌جای shoutrrr از اعلان HTTP داخلی استفاده می‌شود. |
| IP خروجی | به‌صورت پیش‌فرض پویا | بدون گزینه‌های پولی IP ثابت Vercel نمی‌توانید IP مانیتور را در allow-list بگذارید. |
| `vercel dev` | cron را اجرا نمی‌کند | خودتان endpoint را صدا بزنید. |

پلن رایگان Upstash: ۵۰۰ هزار دستور در ماه و ۲۵۶ مگابایت. هر اجرا ۲ دستور مصرف می‌کند (حدود ۱۷ هزار در ماه با زمان‌بندی ۵ دقیقه‌ای).

### Cloudflare Workers (پایتون)
| محدودیت | مقدار | کاری که ما کرده‌ایم |
|---|---|---|
| محیط اجرا | Pyodide (پایتون روی WebAssembly): پایتون ۳٫۱۳، pydantic نسخه ۲٫۱۰، ruamel.yaml نسخه ۰٫۱۸ | فایل `deploy/cloudflare/pyproject.toml` وابستگی‌ها را آزاد نگه می‌دارد. |
| thread / subprocess / فایل sqlite | در دسترس نیست | فقط asyncio؛ وضعیت در KV؛ بدون ping و بدون shoutrrr. |
| TCP | API به نام `connect()` هست ولی IPهای کلودفلر، localhost، IPهای خصوصی و پورت ۲۵ را مسدود می‌کند؛ دسترسی از پایتون تأیید نشد | سایت‌های TCP رد می‌شوند. |
| CPU در هر اجرای cron | **رایگان: ۱۰ میلی‌ثانیه**؛ پولی: ۳۰ ثانیه (بازه کمتر از ۱ ساعت) | بالا آمدن پایتون و pydantic احتمالاً در ۱۰ میلی‌ثانیه جا نمی‌شود: روی **پلن پولی (۵ دلار در ماه)** حساب کنید. |
| زمان واقعی هر اجرای cron | ۱۵ دقیقه | – |
| subrequest در هر اجرا | رایگان ۵۰، پولی ۱۰٬۰۰۰ | هر سایت، هر هشدار و هر فراخوانی KV حساب می‌شود. در پلن رایگان زیر حدود ۴۰ سایت بمانید. |
| اتصال خروجی هم‌زمان | ۶ | بررسی‌ها ۶ تا ۶ تا اجرا می‌شوند. |
| حافظه | ۱۲۸ مگابایت | – |
| cron trigger | رایگان ۵ تا در هر حساب، پولی ۲۵۰؛ به وقت UTC؛ اعمال تغییرات تا ۱۵ دقیقه طول می‌کشد | – |
| KV (وضعیت) | رایگان: ۱۰۰۰ نوشتن در روز و ۱۰۰ هزار خواندن در روز؛ ۱ نوشتن در ثانیه برای هر کلید | هر اجرا یک نوشتن دارد: cron پنج‌دقیقه‌ای ۲۸۸ نوشتن در روز می‌شود. **cron یک‌دقیقه‌ای پلن پولی می‌خواهد.** |
| ابزار | `pywrangler` به uv نسخه ۰٫۱۲٫۳ یا بالاتر نیاز دارد و بسته‌ها را از `index.pyodide.org` می‌گیرد | اول `uv self update`. |

## راه‌اندازی Vercel
1. مخزن را fork کنید یا از template بسازید، `pulsecheck.example.yml` را به `pulsecheck.yml` کپی و ویرایش کنید (آدرس‌های هشدار از نوع `telegram://`، `discord://`، `ntfy://` یا `generic://` و برای رمزها `${VAR}`) و کامیت کنید. اگر نام میزبان‌ها حساس است مخزن را خصوصی نگه دارید.
2. پروژه را بسازید: `vercel` (یا import مخزن در داشبورد). Vercel فایل `app.py` را تشخیص می‌دهد.
3. ذخیره‌ساز اضافه کنید: `vercel install upstash` (Upstash for Redis). متغیرهای `KV_REST_API_URL` / `KV_REST_API_TOKEN` (یا `UPSTASH_REDIS_REST_URL` / `UPSTASH_REDIS_REST_TOKEN`) را تزریق می‌کند؛ هر دو جفت شناخته می‌شوند.
4. متغیرهای محیطی: `CRON_SECRET` (تصادفی، حداقل ۱۶ کاراکتر؛ Vercel آن را به شکل `Authorization: Bearer …` می‌فرستد و endpoint بقیه درخواست‌ها را رد می‌کند) و هر `${VAR}` که در YAML استفاده کرده‌اید.
5. زمان‌بندی: `vercel.json` را ویرایش کنید. Pro: `"schedule": "*/5 * * * *"`. Hobby: زمان‌بندی روزانه را نگه دارید و trigger گیت‌هاب را اضافه کنید: در مخزن GitHub متغیر `VERCEL_CRON_URL` (برابر `https://<project>.vercel.app/api/cron`) و secret با نام `CRON_SECRET` را بگذارید؛ فایل `.github/workflows/trigger-vercel.yml` هر ۵ دقیقه آن را صدا می‌زند.
6. Deploy: `vercel --prod`. بررسی: `curl -H "Authorization: Bearer $CRON_SECRET" https://<project>.vercel.app/api/cron`. پاسخ همه سایت‌ها و وضعیتشان را فهرست می‌کند.

## راه‌اندازی Cloudflare
1. `pulsecheck.example.yml` را به `pulsecheck.yml` کپی و ویرایش کنید (فقط سایت‌های HTTP؛ همان انواع آدرس هشدار).
2. namespace مربوط به KV را بسازید و شناسه‌اش را در `deploy/cloudflare/wrangler.jsonc` بگذارید: `npx wrangler kv namespace create STATE`.
3. `npx wrangler login`، سپس `cd deploy/cloudflare` و secretهای مورد نیاز YAML را اضافه کنید: `npx wrangler secret put TG_TOKEN` (برای هر `${VAR}` یکی).
4. در صورت نیاز `triggers.crons` را در `wrangler.jsonc` عوض کنید.
5. Deploy: `deploy/cloudflare/deploy.sh` (پکیج و YAML شما را داخل Worker کپی می‌کند و بعد `pywrangler deploy` را اجرا می‌کند).
6. لاگ زنده: `npx wrangler tail`.

## نکته YAML
داخل mappingهای درون‌خطی `{ ... }` هر مقداری که `${VAR}` دارد را داخل کوتیشن بگذارید: `{name: api, url: "https://x.example.com/${TOKEN}"}`.

</div>
