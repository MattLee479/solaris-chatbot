from flask import Flask, request, jsonify, render_template, redirect, url_for, session, send_file
import openai, datetime, os
from collections import defaultdict, Counter
import matplotlib.pyplot as plt
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = "Test"  # Change for production!

openai.api_key = os.getenv("OPENAI_API_KEY")

with open("faqs.txt", "r", encoding="utf-8") as f:
    company_info = f.read()

# --- Utility: Log Chat Interactions ---
def log(user, bot, route="OpenAI"):
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open("chat_log.txt", "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] | Route: {route}\nUser: {user}\nBot: {bot}\n\n")

# --- Website Routes ---
@app.route('/')
def home():
    return render_template("index.html")

@app.route('/home')
def home_page():
    return render_template("home.html")

# --- Main Chat Endpoint ---
@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json.get("message", "").lower()

    blocked_words = ["idiot", "scam", "stupid"]
    if any(word in user_message for word in blocked_words):
        reply = "Let's keep this respectful — I'm here to help with solar energy topics."
        log(user_message, reply, route="Blocked")
        return jsonify({"reply": reply})

    if any(kw in user_message for kw in ["joke", "creator", "story", "sing", "who are you", "are you real", "are you a human"]):
        reply = "I'm Solaris AI — a smart assistant designed to help you with UK solar energy services."
        log(user_message, reply, route="Off-Topic")
        return jsonify({"reply": reply})

    if any(kw in user_message for kw in ["quote", "pricing", "cost"]):
        reply = (
            "An average UK solar system can cost between £4,000 and £8,000. "
            "For a personalised quote, please email sales@solarisenergy.co.uk."
        )
        log(user_message, reply, route="Quote")
        return jsonify({"reply": reply})

    if "refund" in user_message:
        reply = "For refund eligibility, please contact support@solarisenergy.co.uk within 14 days of purchase."
        log(user_message, reply, route="Refund")
        return jsonify({"reply": reply})

    if "cancel" in user_message:
        if "appointment" in user_message or "install" in user_message:
            reply = "To cancel an appointment, email support@solarisenergy.co.uk with your booking reference."
        else:
            reply = "To cancel a service, please contact support@solarisenergy.co.uk."
        log(user_message, reply, route="Cancel")
        return jsonify({"reply": reply})

    if "hours" in user_message or "opening" in user_message:
        reply = "We are open Monday to Friday, 9am to 5pm (UK Time)."
        log(user_message, reply, route="Business Hours")
        return jsonify({"reply": reply})

    if "support" in user_message or "problem" in user_message or "warranty" in user_message:
        reply = "For support and warranty enquiries, contact support@solarisenergy.co.uk."
        log(user_message, reply, route="Support")
        return jsonify({"reply": reply})

    if "marketing" in user_message or "collaboration" in user_message:
        reply = "For marketing and collaborations, please email marketing@solarisenergy.co.uk."
        log(user_message, reply, route="Marketing")
        return jsonify({"reply": reply})

    if "general enquiry" in user_message or "contact" in user_message:
        reply = "Please email info@solarisenergy.co.uk for general enquiries."
        log(user_message, reply, route="General Enquiry")
        return jsonify({"reply": reply})

    # Fallback: OpenAI ChatCompletion
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": company_info + "\n\nOnly answer questions related to UK solar panel services. Use GBP (£) and recommend contacting humans for anything else."},
                {"role": "user", "content": user_message}
            ]
        )
        reply = response['choices'][0]['message']['content']
    except Exception as e:
        reply = "Sorry, something went wrong on our side. Please try again shortly."
        print(f"OpenAI Error: {e}")

    log(user_message, reply, route="OpenAI")
    return jsonify({"reply": reply})

# --- Feedback Endpoint ---
@app.route("/feedback", methods=["POST"])
def feedback():
    data = request.json
    rating = data.get("rating")
    comment = data.get("comment", "")
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    with open("feedback_log.txt", "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}]\nRating: {rating}\nComment: {comment}\n\n")

    return jsonify({"message": "Feedback received"})

# --- Admin Panel: Login ---
@app.route('/admin/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['username'] == 'admin' and request.form['password'] == 'solaris123':
            session['logged_in'] = True
            return redirect(url_for('admin'))
        return render_template("login.html", error="Invalid login")
    return render_template("login.html")

# --- Admin Panel: Dashboard ---
@app.route('/admin')
def admin():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    logs = []
    top_questions = Counter()

    try:
        if os.path.exists("chat_log.txt"):
            with open("chat_log.txt", encoding="utf-8", errors="ignore") as f:
                entries = f.read().split("\n\n")
                for entry in entries:
                    if "User:" in entry:
                        question = entry.split("User:")[1].split("<br>")[0].strip()
                        logs.append(entry.replace("\n", "<br>"))
                        top_questions[question.lower()] += 1
    except Exception as e:
        logs.append(f"<i>Error loading chat logs: {e}</i>")

    top_three = top_questions.most_common(3)

    return render_template("admin.html", logs=logs, top_questions=top_three)

# --- Admin Logout ---
@app.route('/admin/logout')
def logout():
    session.clear()
    return redirect(url_for("login"))

# --- Admin Download Logs ---
@app.route('/admin/download')
def download_logs():
    return send_file("chat_log.txt", as_attachment=True)

# --- Admin View Charts ---
@app.route('/admin/charts')
def charts():
    counts = defaultdict(int)
    hours = defaultdict(int)

    question_keywords = {
        "pricing": ["quote", "cost", "price", "pricing"],
        "installation": ["install", "installation", "where do you install"],
        "support": ["support", "problem", "warranty", "issue"],
        "hours": ["hours", "opening", "times"],
        "refunds": ["refund", "return"],
        "general enquiry": ["contact", "info", "general enquiry"],
        "marketing": ["marketing", "collaboration"],
    }

    def classify(text):
        text = text.lower()
        for category, keywords in question_keywords.items():
            if any(word in text for word in keywords):
                return category
        return "other"

    if os.path.exists("chat_log.txt"):
        with open("chat_log.txt", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if "User:" in line:
                    user_text = line.split("User:")[1].strip()
                    category = classify(user_text)
                    counts[category] += 1
                if line.startswith("["):
                    time = line.split("]")[0][1:].split()[1]
                    hour = int(time.split(":")[0])
                    hours[hour] += 1

    # Charts
    if counts:
        plt.clf()
        plt.bar(counts.keys(), counts.values(), color="skyblue")
        plt.title("Most Asked Categories")
        plt.ylabel("Questions Asked")
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig("static/route_chart.png")
    else:
        plt.clf()
        plt.title("No data")
        plt.savefig("static/route_chart.png")

    if hours:
        plt.clf()
        plt.bar(hours.keys(), hours.values(), color="lightgreen")
        plt.title("Chat Volume by Hour")
        plt.xlabel("Hour (0-23)")
        plt.ylabel("Messages")
        plt.xticks(range(24))
        plt.tight_layout()
        plt.savefig("static/hour_chart.png")
    else:
        plt.clf()
        plt.title("No data")
        plt.savefig("static/hour_chart.png")

    return redirect("/admin")

# --- Run the Flask App ---
if __name__ == "__main__":
    app.run(debug=True)
