# ⚡ APEXTASK — Ultimate Gamified To-Do List Web App

> **Vercel Serverless + Cloud MySQL + Single-User JWT Authentication**

A production-grade, gamified productivity suite built with Vanilla JavaScript, Flask Serverless functions, and Cloud MySQL sync across all your devices (Laptop, Mobile, Tablet).

---

## 🌟 Features

- 🔐 **Single-User JWT Authentication** with 7-day persistent login across devices.
- 🎯 **Task Management** with Priority tiers, deadlines, notes, and lifecycle history.
- 🔁 **Cross-Day Carry Forward** (Auto & manual rollover with chain tracking).
- 📊 **Dashboards & Visualizations**:
  - **Weekly Velocity Bar Chart** with Peak Day momentum tracker.
  - **Monthly Activity Heatmap** with 5-tier intensity matrix.
  - **Yearly Performance Matrix** with 365-day GitHub-style pixel grid and 12-month trajectory line chart (Chart.js).
- 🏆 **Gamification Engine**:
  - XP rewards & 1.5x Level scaling.
  - Daily completion streaks & Slacker mode warnings.
  - 11 Prestige Badges in the **Trophy Vault**.
  - **Mystery Reward Chest** unlocking every 10 conquered tasks.
- 🔊 **Web Audio Synthesizer**: Procedurally generated chimes, fanfares, and alerts.
- 🎨 **3 Themes**: Dark Obsidian, Aura Cyberpunk (Glassmorphic), Light Frosted.
- 📱 **Mobile & Desktop Responsive**: Native PWA feel with zero frameworks.

---

## 🚀 How to Deploy to Vercel

### Step 1: Push Code to GitHub
1. Initialize a git repository and push to GitHub:
   ```bash
   git init
   git add .
   git commit -m "Initial commit of ApexTask Vercel app"
   git branch -M main
   git remote add origin https://github.com/your-username/apextask.git
   git push -u origin main
   ```

### Step 2: Set Up Free Cloud MySQL (PlanetScale or Railway)
1. Create a MySQL database on [PlanetScale](https://planetscale.com) or [Railway](https://railway.app).
2. Run the SQL schema from [`database/schema.sql`](database/schema.sql) in your cloud MySQL query console.

### Step 3: Import Project to Vercel
1. Go to [vercel.com](https://vercel.com) and click **Add New... → Project**.
2. Select your GitHub repository.
3. In **Settings → Environment Variables**, add the following:

| Variable | Example Value | Description |
| :--- | :--- | :--- |
| `APP_USERNAME` | `mayur` | Single user login username |
| `APP_PASSWORD` | `mayur123` | Single user password (or bcrypt hash) |
| `JWT_SECRET` | `your-secure-jwt-secret-string-here` | Secret key for signing JWTs |
| `MYSQL_HOST` | `roundhouse.proxy.rlwy.net` | Cloud MySQL host |
| `MYSQL_PORT` | `3306` | Cloud MySQL port |
| `MYSQL_USER` | `root` | Database username |
| `MYSQL_PASSWORD` | `your-db-password` | Database password |
| `MYSQL_DB` | `todo_app` | Database name |

4. Click **Deploy**!
5. Open your live Vercel URL (e.g., `https://your-apextask.vercel.app`), log in, and use everywhere!

---

## 💻 Local Development

1. Install dependencies:
   ```bash
   pip install -r api/requirements.txt
   ```
2. Start the local server:
   ```bash
   python api/index.py
   ```
3. Open `http://127.0.0.1:5000` in your browser.
4. Log in with `mayur` / `mayur123`.
