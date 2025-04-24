from flask import Flask, request, jsonify, render_template, redirect, url_for, session, send_file
import openai, datetime, os
from collections import defaultdict
import matplotlib.pyplot as plt

app = Flask(__name__)
app.secret_key = "Test"  # Change this to a secure value
openai.api_key = "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"

# Load company info
with open("faqs.txt", "r") as f:
    company_info = f.read()

# Log all chats
def log(user, bot, route="OpenAI"):
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open("chat_log.txt", "a") as f:
        f.write(f"[{timestamp}] | Route: {route}\nUser: {user}\nBot: {bot}\n\n")

@app.route('/')
def home():
    return render_template("index.html")

@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json.get("message", "").lower()

    blocked_words = ["idiot", "scam", "stupid"]
    if any(word in user_message for word in blocked_words):
        reply = "Let's keep this respectful — I'm here to help with solar energy topics."
        log(user_message, reply, route="Blocked")
        return jsonify({"reply": reply})

    if any(kw in user_message for kw in ["joke", "creator", "story", "sing", "who are you"]):
        reply = "I'm your solar assistant, here to answer questions about our services or solar energy in the UK."
        log(user_message, reply, route="Off-Topic")
        return jsonify({"reply": reply})

    if "quote" in user_message or "pricing" in user_message or "cost" in user_message:
        reply = (
            "An average UK solar system can cost between £4,000 and £8,000. "
            "This is only an estimate — please email sales@solarisenergy.co.uk for a personalised quote."
        )
        log(user_message, reply, route="Quote")
        return jsonify({"reply": reply})

    if "refund" in user_message:
        reply = "For refund eligibility, please contact support@solarisenergy.co.uk within 14 days of purchase."
        log(user_message, reply, route="Refund")
        return jsonify({"reply": reply})

    if "cancel" in user_message:
        route = "Cancel"
        if "appointment" in user_message or "install" in user_message:
            reply = "To cancel an appointment, email support@solarisenergy.co.uk with your booking reference."
        else:
            reply = "To cancel a service, please contact support@solarisenergy.co.uk."
        log(user_message, reply, route=route)
        return jsonify({"reply": reply})

    if "hours" in user_message or "opening" in user_message:
        reply = "We're open Monday to Friday, 9am to 5pm (UK time)."
        log(user_message, reply, route="Business Hours")
        return jsonify({"reply": reply})

    if "support" in user_message or "problem" in user_message or "warranty" in user_message:
        reply = "Please reach out to support@solarisenergy.co.uk for technical issues or warranty enquiries."
        log(user_message, reply, route="Support")
        return jsonify({"reply": reply})

    if "marketing" in user_message or "collaboration" in user_message:
        reply = "You can contact marketing@solarisenergy.co.uk for any collaboration or press enquiries."
        log(user_message, reply, route="Marketing")
        return jsonify({"reply": reply})

    if "general enquiry" in user_message or "contact" in user_message:
        reply = "Please email info@solarisenergy.co.uk for general enquiries."
        log(user_message, reply, route="General Enquiry")
        return jsonify({"reply": reply})

    # Fallback to OpenAI
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": company_info + "\n\nOnly answer questions related to UK solar panel services. Use GBP and refer people to human contacts as needed."},
                {"role": "user", "content": user_message}
            ]
        )
        reply = response['choices'][0]['message']['content']
    except Exception as e:
        reply = "Sorry, something went wrong while processing that. Please try again later."

    log(user_message, reply, route="OpenAI")
    return jsonify({"reply": reply})

# ------------- Feedback Logging (1–10) ------------- #
@app.route("/feedback", methods=["POST"])
def feedback():
    data = request.json
    rating = data.get("rating")
    comment = data.get("comment", "")
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    with open("feedback_log.txt", "a") as f:
        f.write(f"[{timestamp}]\nRating: {rating}\nComment: {comment}\n\n")

    return jsonify({"message": "Feedback received"})

# ---------------- Admin Panel ---------------- #
@app.route('/admin/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['username'] == 'admin' and request.form['password'] == 'solaris123':
            session['logged_in'] = True
            return redirect(url_for('admin'))
        else:
            return render_template("login.html", error="Invalid login")
    return render_template("login.html")

@app.route('/admin')
def admin():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    logs = []
    if os.path.exists("chat_log.txt"):
        with open("chat_log.txt") as f:
            entries = f.read().split("\n\n")
            for entry in entries:
                if "User:" in entry:
                    logs.append(entry.replace("\n", "<br>"))

    return render_template("admin.html", logs=logs)

@app.route('/admin/logout')
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route('/admin/download')
def download_logs():
    return send_file("chat_log.txt", as_attachment=True)

@app.route('/admin/charts')
def charts():
    counts = defaultdict(int)
    hours = defaultdict(int)

    if os.path.exists("chat_log.txt"):
        with open("chat_log.txt") as f:
            for line in f:
                if "Route:" in line:
                    route = line.split("Route:")[1].split("\n")[0].strip()
                    counts[route] += 1
                if line.startswith("["):
                    time = line.split("]")[0][1:].split()[1]
                    hour = int(time.split(":")[0])
                    hours[hour] += 1

    # Chat route chart
    plt.clf()
    plt.bar(counts.keys(), counts.values(), color="skyblue")
    plt.title("Most Asked Categories")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig("static/route_chart.png")

    # Usage by hour chart
    plt.clf()
    plt.bar(hours.keys(), hours.values(), color="lightgreen")
    plt.title("Peak Usage by Hour")
    plt.tight_layout()
    plt.savefig("static/hour_chart.png")

    # Feedback rating chart
    feedback_counts = defaultdict(int)
    if os.path.exists("feedback_log.txt"):
        with open("feedback_log.txt") as f:
            for line in f:
                if "Rating:" in line:
                    val = line.strip().split("Rating:")[1].strip()
                    if val.isdigit():
                        feedback_counts[int(val)] += 1

        if feedback_counts:
            plt.clf()
            plt.bar(feedback_counts.keys(), feedback_counts.values(), color="orange")
            plt.title("Feedback Ratings (1–10)")
            plt.xlabel("Rating")
            plt.ylabel("Responses")
            plt.tight_layout()
            plt.savefig("static/feedback_chart.png")

    return redirect("/admin")

# ---------------- Run App ---------------- #
if __name__ == "__main__":
    app.run(debug=True)
