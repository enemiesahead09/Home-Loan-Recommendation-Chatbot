"""
Home Loan Advisor Chatbot

A Streamlit app that helps users:
- Enter a borrower profile in a guided advisor-style form
- Calculate EMI and basic loan eligibility
- Ask home loan questions using the Groq API

Run with:
    streamlit run home_loan_chatbot.py
"""

import math
import os

import streamlit as st
from dotenv import load_dotenv
from groq import Groq


load_dotenv()


def get_groq_client():
    """Return a Groq client if the API key exists, otherwise return None."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return None
    return Groq(api_key=api_key)


def get_model_name():
    """Allow model override through .env while keeping a beginner-friendly default."""
    return os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")


def suggest_interest_rate(credit_score):
    """Return an estimated annual interest rate based on credit score."""
    if credit_score >= 800:
        return 8.1
    if credit_score >= 750:
        return 8.5
    if credit_score >= 700:
        return 9.0
    if credit_score >= 650:
        return 10.0
    return 11.5


def calculate_emi(loan_amount, annual_interest_rate, tenure_years):
    """Calculate monthly EMI using the standard loan EMI formula."""
    months = int(tenure_years * 12)
    if months <= 0:
        raise ValueError("Tenure must be greater than zero.")

    monthly_rate = annual_interest_rate / 12 / 100

    if monthly_rate == 0:
        return loan_amount / months

    factor = math.pow(1 + monthly_rate, months)
    return loan_amount * monthly_rate * factor / (factor - 1)


def estimate_max_loan(monthly_emi_capacity, annual_interest_rate, tenure_years):
    """Estimate the maximum loan amount for a given EMI capacity."""
    months = int(tenure_years * 12)
    if months <= 0:
        return 0

    monthly_rate = annual_interest_rate / 12 / 100

    if monthly_rate == 0:
        return monthly_emi_capacity * months

    factor = math.pow(1 + monthly_rate, months)
    return monthly_emi_capacity * (factor - 1) / (monthly_rate * factor)


def check_eligibility(monthly_income, loan_amount, tenure_years, credit_score, annual_interest_rate):
    """
    Perform a beginner-friendly eligibility check.
    Logic used:
    - Maximum affordable EMI is 45% of monthly income
    - Credit score affects rate suggestion and guidance
    """
    if monthly_income <= 0:
        raise ValueError("Monthly income must be greater than zero.")

    emi = calculate_emi(loan_amount, annual_interest_rate, tenure_years)
    max_affordable_emi = monthly_income * 0.45
    max_loan_amount = estimate_max_loan(max_affordable_emi, annual_interest_rate, tenure_years)

    eligible = emi <= max_affordable_emi and credit_score >= 650

    if credit_score < 650:
        message = "Low credit score may reduce approval chances. Improving the score can help."
    elif eligible:
        message = "You appear broadly eligible based on this simple income-to-EMI check."
    else:
        message = "The requested loan may be high for the current income. Consider a lower loan or longer tenure."

    return {
        "eligible": eligible,
        "emi": emi,
        "max_affordable_emi": max_affordable_emi,
        "max_loan_amount": max_loan_amount,
        "message": message,
    }


def build_financial_context(profile, annual_interest_rate, results):
    """Create short context text for the chatbot so replies stay relevant."""
    if results:
        result_text = (
            f"Estimated EMI: {results['emi']:.2f} INR per month. "
            f"Maximum affordable EMI: {results['max_affordable_emi']:.2f} INR. "
            f"Estimated maximum loan amount: {results['max_loan_amount']:.2f} INR. "
            f"Eligibility status: {'Eligible' if results['eligible'] else 'Not clearly eligible'}."
        )
    else:
        result_text = "No EMI or eligibility calculation has been run yet."

    return (
        f"User profile: gender = {profile['gender']}, marital status = {profile['marital_status']}, "
        f"dependents = {profile['dependents']}, education = {profile['education_level']}, "
        f"self employed = {profile['self_employed']}, income frequency = {profile['income_frequency']}, "
        f"applicant income = {profile['applicant_income']:.2f} INR, co-applicant income = {profile['coapplicant_income']:.2f} INR, "
        f"total monthly income = {profile['monthly_income']:.2f} INR, requested loan amount = {profile['loan_amount']:.2f} INR, "
        f"tenure = {profile['tenure_years']} years, credit score = {profile['credit_score']}, "
        f"estimated interest rate = {annual_interest_rate:.2f}%."
        f" {result_text}"
    )


def get_chatbot_reply(client, model, chat_history, financial_context):
    """Send the conversation and financial context to Groq and return the assistant reply."""
    system_prompt = (
        "You are a helpful home loan advisor chatbot. "
        "Answer clearly and simply. "
        "Help with home loan eligibility, EMI, interest rates, repayment planning, and suggestions. "
        "Do not claim guaranteed loan approval. "
        "Use the user's financial context when relevant."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "system", "content": f"Financial context: {financial_context}"},
    ]

    for message in chat_history:
        messages.append({"role": message["role"], "content": message["content"]})

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.4,
    )

    reply_text = response.choices[0].message.content.strip() if response.choices else ""
    if not reply_text:
        return "I could not generate a response just now. Please try asking your question again."
    return reply_text


def apply_custom_theme():
    """Inject custom CSS to create a dark advisor-style interface."""
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&display=swap');

        :root {
            --bg: #090d16;
            --panel: #0d121d;
            --panel-soft: #121826;
            --field: #232633;
            --field-border: #30384a;
            --text: #f6f4ee;
            --muted: #98a1b3;
            --accent: #ff5d63;
            --accent-soft: rgba(255, 93, 99, 0.18);
            --success: #43c59e;
            --warning: #ffb454;
        }

        html, body, [class*="css"] {
            font-family: 'Manrope', sans-serif;
        }

        .stApp {
            background:
                radial-gradient(circle at top left, rgba(116, 72, 255, 0.16), transparent 26%),
                radial-gradient(circle at top right, rgba(255, 93, 99, 0.12), transparent 22%),
                linear-gradient(180deg, #090d16 0%, #0b1019 48%, #090d16 100%);
            color: var(--text);
        }

        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
            max-width: 1240px;
        }

        h1, h2, h3, p, label, span, div {
            color: var(--text);
        }

        [data-testid="stHeader"] {
            background: rgba(9, 13, 22, 0.65);
        }

        [data-testid="stSidebar"] {
            background: #0a0f18;
        }

        .hero-shell {
            border: 1px solid rgba(255, 255, 255, 0.08);
            background: linear-gradient(180deg, rgba(13, 18, 29, 0.96), rgba(10, 14, 22, 0.92));
            border-radius: 26px;
            padding: 18px 22px 24px;
            box-shadow: 0 28px 80px rgba(0, 0, 0, 0.35);
            margin-bottom: 1.5rem;
        }

        .hero-kicker {
            color: #f3b36b;
            text-transform: uppercase;
            letter-spacing: 0.18em;
            font-size: 0.76rem;
            font-weight: 800;
            margin-bottom: 0.55rem;
        }

        .hero-title {
            font-size: clamp(2rem, 4vw, 3.2rem);
            line-height: 1.05;
            font-weight: 800;
            margin: 0;
        }

        .hero-subtitle {
            color: var(--muted);
            font-size: 1rem;
            margin-top: 0.85rem;
            max-width: 760px;
        }

        .section-card {
            border: 1px solid rgba(255, 255, 255, 0.08);
            background: linear-gradient(180deg, rgba(13, 18, 29, 0.98), rgba(10, 13, 21, 0.98));
            border-radius: 24px;
            padding: 1.1rem 1.1rem 1.25rem;
            margin-bottom: 1.25rem;
        }

        .section-title {
            font-size: 1.05rem;
            font-weight: 800;
            margin-bottom: 0.25rem;
        }

        .section-subtitle {
            color: var(--muted);
            font-size: 0.92rem;
            margin-bottom: 1rem;
        }

        [data-testid="stSelectbox"] label,
        [data-testid="stNumberInput"] label,
        [data-testid="stRadio"] label,
        [data-testid="stSlider"] label {
            font-size: 0.92rem;
            font-weight: 700;
            color: #e8ebf4;
        }

        div[data-baseweb="select"] > div,
        [data-testid="stNumberInput"] > div > div > input,
        [data-testid="stTextInput"] input {
            background: var(--field) !important;
            border: 1px solid var(--field-border) !important;
            border-radius: 14px !important;
            color: var(--text) !important;
            min-height: 48px;
        }

        [data-testid="stNumberInput"] button {
            color: var(--text) !important;
        }

        [data-baseweb="radio"] > div {
            gap: 0.85rem;
        }

        [data-testid="stRadio"] label[data-baseweb="radio"] {
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid rgba(255, 255, 255, 0.07);
            border-radius: 999px;
            padding: 0.3rem 0.9rem 0.3rem 0.4rem;
        }

        [data-testid="stSlider"] [role="slider"] {
            background: var(--accent);
            border: 2px solid rgba(255, 255, 255, 0.24);
        }

        [data-testid="stSlider"] div[data-baseweb="slider"] > div > div {
            background: linear-gradient(90deg, var(--accent), #ff7a59);
        }

        .stButton > button {
            width: 100%;
            min-height: 52px;
            border-radius: 16px;
            border: 1px solid rgba(255, 255, 255, 0.08);
            background: linear-gradient(90deg, #ff5d63, #ff7a59);
            color: white;
            font-size: 1rem;
            font-weight: 800;
            box-shadow: 0 18px 50px rgba(255, 93, 99, 0.25);
        }

        .metric-card {
            border: 1px solid rgba(255, 255, 255, 0.08);
            background: linear-gradient(180deg, rgba(18, 24, 38, 0.96), rgba(12, 17, 28, 0.96));
            border-radius: 20px;
            padding: 1rem 1.1rem;
            min-height: 126px;
        }

        .metric-label {
            color: var(--muted);
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            margin-bottom: 0.5rem;
        }

        .metric-value {
            font-size: 1.75rem;
            font-weight: 800;
            line-height: 1.05;
        }

        .metric-note {
            color: var(--muted);
            margin-top: 0.55rem;
            font-size: 0.92rem;
        }

        .insight-card {
            border-radius: 18px;
            padding: 1rem 1.1rem;
            border: 1px solid rgba(255, 255, 255, 0.06);
            margin-top: 1rem;
            font-weight: 600;
        }

        .insight-good {
            background: rgba(67, 197, 158, 0.08);
            color: #abf0d7;
        }

        .insight-caution {
            background: rgba(255, 180, 84, 0.1);
            color: #ffd8a1;
        }

        [data-testid="stChatMessage"] {
            background: rgba(16, 21, 33, 0.86);
            border: 1px solid rgba(255, 255, 255, 0.06);
            border-radius: 18px;
            padding: 0.2rem 0.35rem;
        }

        [data-testid="stChatInput"] textarea {
            background: var(--field) !important;
            border: 1px solid var(--field-border) !important;
        }

        </style>
        """,
        unsafe_allow_html=True,
    )


def render_metric_card(label, value, note):
    """Render a styled metric block using HTML."""
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-note">{note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def main():
    """Build and run the Streamlit UI."""
    st.set_page_config(page_title="Home Loan Advisor", page_icon="H", layout="wide")
    apply_custom_theme()

    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": (
                    "I can help with home loan eligibility, EMI, interest rates, and repayment planning. "
                    "Fill in your profile, generate your estimate, and then ask anything you want to explore."
                ),
            }
        ]

    if "calculation_result" not in st.session_state:
        st.session_state.calculation_result = None

    st.markdown(
        """
        <div class="hero-shell">
            <div class="hero-kicker">Home Loan Advisor</div>
            <h1 class="hero-title">Tell Us About Yourself</h1>
            <p class="hero-subtitle">
                A guided profile form inspired by modern loan advisor dashboards. Share your details, review your
                EMI outlook, and get personalized guidance in one place.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    left_col, right_col = st.columns(2, gap="large")

    with left_col:
        gender = st.selectbox("Gender", ["Male", "Female", "Other"], index=0)
        marital_status = st.selectbox("Marital Status", ["Yes", "No"], index=0)
        dependents = st.number_input("Number of Dependents", min_value=0, max_value=10, value=0, step=1)
        education_level = st.selectbox("Education Level", ["Graduate", "Not Graduate", "Postgraduate"], index=0)
        self_employed = st.selectbox("Self-Employed", ["Yes", "No"], index=0)

    with right_col:
        income_frequency = st.radio("Is your income monthly or yearly?", ["Monthly", "Yearly"], horizontal=False)
        applicant_income = st.number_input("Applicant Income (Rs)", min_value=0.0, value=50000.0, step=1000.0)
        coapplicant_income = st.number_input("Co-Applicant Income (Rs)", min_value=0.0, value=0.0, step=1000.0)
        loan_amount_lakhs = st.number_input("Loan Amount Needed (Rs Lakhs)", min_value=0.0, value=50.0, step=1.0)
        tenure_years = st.slider("Loan Duration (Years)", min_value=1, max_value=30, value=15, step=1)
        credit_band = st.selectbox("Credit Score", ["<600", "600-649", "650-699", "700-749", "750-799", "800+"], index=0)

    credit_score_map = {
        "<600": 580,
        "600-649": 625,
        "650-699": 675,
        "700-749": 725,
        "750-799": 775,
        "800+": 820,
    }
    credit_score = credit_score_map[credit_band]

    raw_total_income = applicant_income + coapplicant_income
    monthly_income = raw_total_income if income_frequency == "Monthly" else raw_total_income / 12
    loan_amount = loan_amount_lakhs * 100000
    estimated_rate = suggest_interest_rate(credit_score)

    if st.button("Get Personalized Advice", use_container_width=True):
        try:
            if loan_amount <= 0:
                raise ValueError("Loan amount must be greater than zero.")

            st.session_state.calculation_result = check_eligibility(
                monthly_income=monthly_income,
                loan_amount=loan_amount,
                tenure_years=tenure_years,
                credit_score=credit_score,
                annual_interest_rate=estimated_rate,
            )
        except ValueError as error:
            st.session_state.calculation_result = None
            st.error(str(error))
        except Exception as error:
            st.session_state.calculation_result = None
            st.error(f"Something went wrong during calculation: {error}")

    results = st.session_state.calculation_result

    if results:
        st.markdown(
            """
            <div class="section-card">
                <div class="section-title">Personalized Snapshot</div>
                <div class="section-subtitle">A quick read on affordability, EMI pressure, and how much loan capacity this income level may support.</div>
            """,
            unsafe_allow_html=True,
        )

        metric1, metric2, metric3 = st.columns(3, gap="medium")
        with metric1:
            render_metric_card("Estimated EMI", f"Rs {results['emi']:,.0f}", f"At {estimated_rate:.2f}% for {tenure_years} years")
        with metric2:
            render_metric_card(
                "Monthly Affordable EMI",
                f"Rs {results['max_affordable_emi']:,.0f}",
                "Based on 45% of total monthly income",
            )
        with metric3:
            render_metric_card(
                "Estimated Max Loan",
                f"Rs {results['max_loan_amount']:,.0f}",
                "Approximate supported principal for this profile",
            )

        status_class = "insight-good" if results["eligible"] else "insight-caution"
        profile_note = (
            f"Combined monthly income used for evaluation: Rs {monthly_income:,.0f}. "
            f"Requested amount: Rs {loan_amount:,.0f}. Credit estimate: {credit_score}."
        )
        st.markdown(
            f"""
            <div class="insight-card {status_class}">
                {results['message']}<br><br>{profile_note}
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown(
        """
        <div class="section-card">
            <div class="section-title">Loan Assistant Chat</div>
            <div class="section-subtitle">Ask follow-up questions about EMI, approval chances, required documents, or repayment strategy.</div>
        """,
        unsafe_allow_html=True,
    )

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    prompt = st.chat_input("Ask a question about home loans...")

    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        client = get_groq_client()
        if client is None:
            error_message = (
                "Groq API key not found. Please create a `.env` file and add `GROQ_API_KEY=your_key_here`."
            )
            st.session_state.messages.append({"role": "assistant", "content": error_message})
            with st.chat_message("assistant"):
                st.error(error_message)
        else:
            profile = {
                "gender": gender,
                "marital_status": marital_status,
                "dependents": dependents,
                "education_level": education_level,
                "self_employed": self_employed,
                "income_frequency": income_frequency,
                "applicant_income": applicant_income,
                "coapplicant_income": coapplicant_income,
                "monthly_income": monthly_income,
                "loan_amount": loan_amount,
                "tenure_years": tenure_years,
                "credit_score": credit_score,
            }

            financial_context = build_financial_context(
                profile=profile,
                annual_interest_rate=estimated_rate,
                results=results,
            )

            try:
                with st.chat_message("assistant"):
                    with st.spinner("Thinking..."):
                        reply = get_chatbot_reply(
                            client=client,
                            model=get_model_name(),
                            chat_history=st.session_state.messages,
                            financial_context=financial_context,
                        )
                    st.markdown(reply)

                st.session_state.messages.append({"role": "assistant", "content": reply})
            except Exception as error:
                error_message = f"Unable to get chatbot response right now: {error}"
                st.session_state.messages.append({"role": "assistant", "content": error_message})
                with st.chat_message("assistant"):
                    st.error(error_message)

    st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
