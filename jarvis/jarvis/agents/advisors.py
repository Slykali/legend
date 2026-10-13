"""Advisor agents: planning, tutoring, fitness and personal finance."""
from __future__ import annotations

from ..agent import Agent
from ..tools import Tool, build_tool, tool
from .math import MathAgent
from .personal import NotesAgent, TasksAgent


def _borrow(agent: Agent, *names: str) -> list[Tool]:
    return [build_tool(getattr(agent, n)) for n in names]


class PlannerAgent(Agent):
    name = "planner"
    title = "Planner"
    description = ("Breaks goals into concrete plans: projects, trips, study or work schedules, "
                   "events. Can save the plan as a note and add the steps as to-dos.")
    instructions = ("You are a strategic planner. Produce clear, realistic, step-by-step plans "
                    "with time estimates. Only save notes or to-dos if the user asked you to.")
    temperature = 0.5

    def get_tools(self) -> list[Tool]:
        return (_borrow(NotesAgent(self.ctx), "create_note")
                + _borrow(TasksAgent(self.ctx), "add_todo", "set_reminder"))


class TutorAgent(Agent):
    name = "tutor"
    title = "Tutor"
    description = "Explains concepts step by step at any level, creates quizzes and flashcards."
    instructions = ("You are a patient expert tutor. Explain with intuition first, then detail, "
                    "use examples and analogies, and check understanding with a short question.")
    temperature = 0.5


class FitnessAgent(Agent):
    name = "fitness"
    title = "Fitness"
    description = ("Personal trainer and nutrition coach: workout plans, exercise form tips, "
                   "calories, macros, BMI and progress advice.")
    instructions = ("You are a certified personal trainer and sports nutritionist. Give safe, "
                    "practical advice; suggest seeing a professional for medical issues. Use the "
                    "tools for any numbers.")
    temperature = 0.4

    def get_tools(self) -> list[Tool]:
        return _borrow(MathAgent(self.ctx), "calculate", "convert_units") + super().get_tools()

    @tool
    def body_metrics(self, weight_kg: float, height_cm: float, age: int, sex: str = "male",
                     activity: str = "moderate") -> dict:
        """Compute BMI, BMR (Mifflin-St Jeor) and daily calorie needs.

        Args:
            weight_kg: Body weight in kilograms.
            height_cm: Height in centimetres.
            age: Age in years.
            sex: 'male' or 'female'.
            activity: sedentary, light, moderate, active or very_active.
        """
        bmi = weight_kg / (height_cm / 100) ** 2
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age + (5 if sex.lower().startswith("m") else -161)
        factor = {"sedentary": 1.2, "light": 1.375, "moderate": 1.55, "active": 1.725,
                  "very_active": 1.9}.get(activity.lower(), 1.55)
        tdee = bmr * factor
        category = ("underweight" if bmi < 18.5 else "healthy" if bmi < 25
                    else "overweight" if bmi < 30 else "obese")
        return {"bmi": round(bmi, 1), "bmi_category": category, "bmr_kcal": round(bmr),
                "maintenance_kcal": round(tdee), "fat_loss_kcal": round(tdee - 500),
                "muscle_gain_kcal": round(tdee + 300),
                "protein_g_range": f"{round(weight_kg * 1.6)}-{round(weight_kg * 2.2)}"}


class FinanceAgent(Agent):
    name = "finance"
    title = "Finance"
    description = ("Personal finance: budgets, savings goals, loan/mortgage payments, compound "
                   "interest, splitting bills.")
    instructions = ("You are a careful personal finance assistant (not a licensed adviser). "
                    "Always compute numbers with tools and show the key figures.")
    temperature = 0.2

    def get_tools(self) -> list[Tool]:
        return _borrow(MathAgent(self.ctx), "calculate") + super().get_tools()

    @tool
    def loan_payment(self, principal: float, annual_rate_percent: float, years: float) -> dict:
        """Monthly payment and total interest for a loan or mortgage.

        Args:
            principal: Amount borrowed.
            annual_rate_percent: Interest rate per year, e.g. 5.5.
            years: Loan term in years.
        """
        n = round(years * 12)
        r = annual_rate_percent / 100 / 12
        payment = principal / n if r == 0 else principal * r / (1 - (1 + r) ** -n)
        return {"monthly_payment": round(payment, 2), "total_paid": round(payment * n, 2),
                "total_interest": round(payment * n - principal, 2), "payments": n}

    @tool
    def compound_growth(self, initial: float, monthly_contribution: float,
                        annual_return_percent: float, years: float) -> dict:
        """Future value of savings/investments with monthly contributions.

        Args:
            initial: Starting amount.
            monthly_contribution: Amount added each month.
            annual_return_percent: Expected yearly return, e.g. 7.
            years: Number of years.
        """
        r = annual_return_percent / 100 / 12
        balance = initial
        for _ in range(round(years * 12)):
            balance = balance * (1 + r) + monthly_contribution
        contributed = initial + monthly_contribution * round(years * 12)
        return {"future_value": round(balance, 2), "total_contributed": round(contributed, 2),
                "growth": round(balance - contributed, 2)}

    @tool
    def budget_split(self, monthly_income: float, needs_percent: float = 50,
                     wants_percent: float = 30, savings_percent: float = 20) -> dict:
        """Split income into needs/wants/savings (50/30/20 by default).

        Args:
            monthly_income: Net income per month.
            needs_percent: Share for essentials.
            wants_percent: Share for discretionary spending.
            savings_percent: Share for savings and debt repayment.
        """
        return {k: round(monthly_income * p / 100, 2) for k, p in
                (("needs", needs_percent), ("wants", wants_percent), ("savings", savings_percent))}
