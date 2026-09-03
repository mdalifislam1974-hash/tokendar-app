# TokenDar Telegram Mining Bot — starter project

এটি ছবির মতো Telegram Mini App ভিত্তিক একটি **reward-points mining demo**। এটি নিজে থেকে বাস্তব cryptocurrency mine করে না।

## চালু করার ধাপ

1. Telegram-এ `@BotFather` দিয়ে bot তৈরি করে token নাও।
2. Python 3.10+ server-এ এই project upload করো।
3. Install:
   `pip install -r requirements.txt`
4. Bot token set করো:
   `BOT_TOKEN=YOUR_TOKEN`
5. `WEBAPP_URL`-এ তোমার HTTPS Mini App URL দাও।
6. Bot চালাও:
   `python bot.py`
7. Web app চালাও:
   `python app.py`

**গুরুত্বপূর্ণ:** production-এ `/api/claim`-এর আগে Telegram WebApp `initData` server-side validate করতে হবে। এই starter-এ সেটা ইচ্ছাকৃতভাবে বাদ রাখা হয়েছে যাতে demo সহজে বোঝা যায়।

## পরিবর্তন করার জায়গা

`bot.py`-এর `RATE_PER_HOUR = 0.0985` এবং `MINING_HOURS = 4` পরিবর্তন করে mining rate/period বদলানো যাবে।

পরের ধাপে যোগ করা যায়:
- Referral bonus
- Tasks / channel join verification
- Leaderboard
- Admin panel
- Withdrawal request
- PostgreSQL
- Telegram Stars বা অন্য বৈধ reward/payment integration
