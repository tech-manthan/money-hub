"""Niche profiles. The offline library covers common niches; any other niche text gets a generic profile
(and, when an LLM is available, a freshly researched profile via `research_niche`)."""
from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field


class NicheProfile(BaseModel):
    key: str
    name: str
    audience: str
    tone: str = "warm, encouraging, practical"
    mood: str = "calm"
    tagline: str = ""
    weekly_boxes: list[str] = Field(default_factory=list, description="4-6 labelled boxes on the weekly spread")
    daily_labels: list[str] = Field(default_factory=list, description="3-5 tiny daily check items")
    habits: list[str] = Field(default_factory=list)
    prompts: list[str] = Field(default_factory=list, description="Niche-specific journal prompts")
    affirmations: list[str] = Field(default_factory=list)
    seo_keywords: list[str] = Field(default_factory=list)
    worksheet_topics: list[str] = Field(default_factory=list)
    budget_extra: list[str] = Field(default_factory=list, description="Extra budget categories for this niche")
    pain_points: list[str] = Field(default_factory=list)


def _n(key, name, audience, mood, tagline, boxes, daily, habits, prompts, affirm, kw, topics, pains,
       tone="warm, encouraging, practical", budget=()):
    return NicheProfile(
        key=key, name=name, audience=audience, mood=mood, tagline=tagline, tone=tone,
        weekly_boxes=list(boxes), daily_labels=list(daily), habits=list(habits), prompts=list(prompts),
        affirmations=list(affirm), seo_keywords=list(kw), worksheet_topics=list(topics),
        pain_points=list(pains), budget_extra=list(budget),
    )


LIBRARY: dict[str, NicheProfile] = {}
ALIASES: dict[str, str] = {}


def _add(profile: NicheProfile, *aliases: str):
    LIBRARY[profile.key] = profile
    for a in (profile.key, profile.name.lower(), *aliases):
        ALIASES[a.lower()] = profile.key


_add(_n(
    "adhd", "ADHD", "adults and teens with ADHD who struggle with planning and follow-through", "soft",
    "Plan for the brain you have, not the one you wish you had.",
    ["Brain dump", "Top 3 (just three!)", "Time-blind check: appointments", "Dopamine menu win", "Doing it later (parking lot)", "Meds & energy check"],
    ["Meds", "Water", "Movement", "Body-double time"],
    ["Take meds", "5-minute tidy", "Drink water", "Move your body", "Eat a real meal", "Plan tomorrow", "Phone away at night", "One tiny task before noon"],
    ["What is the smallest first step for the thing I keep avoiding?", "When was my focus best today, and what was happening around me?", "What would make starting feel 10% easier?", "Which task is bigger in my head than in reality?", "What did I do today that I would have called impossible last month?", "Which reminders actually work for me, and which do I ignore?", "What drains my energy that I can say no to this week?", "How do I want to treat myself when I finish something hard?", "What does a good-enough day look like?", "Who could I body-double with this week?"],
    ["Done is better than perfect.", "My brain is different, not broken.", "Small steps still count.", "I can restart as many times as I need.", "Rest is part of the plan.", "I am allowed to make things easy.", "Progress, not perfection.", "I work with my brain, not against it."],
    ["adhd planner", "adhd printable", "neurodivergent planner", "adhd daily planner", "executive function", "adhd organizer", "undated planner", "brain dump page"],
    ["Break a big task into tiny steps", "Time estimation practice", "Build a dopamine menu", "Morning routine builder", "Weekly reset checklist", "Body-doubling plan"],
    ["Overwhelm from too many tasks", "Forgetting appointments", "Planners that feel like pressure"],
), "attention deficit", "neurodivergent", "add")

_add(_n(
    "teacher", "Teacher", "K-12 teachers and homeschool parents", "fresh",
    "Plan the week, protect your evenings.",
    ["Weekly objectives", "Lessons to prep", "Grading queue", "Parent contacts", "Copies & supplies", "Small wins"],
    ["Prep done", "Grading", "Parent call", "Self-care"],
    ["Prep tomorrow's lesson", "Grade 5 assignments", "Positive parent message", "Tidy classroom 5 min", "Drink water", "Leave on time", "Plan one fun activity", "Reflect on one win"],
    ["Which lesson landed best this week and why?", "Which student needs a check-in tomorrow?", "What did I do this week that I want to repeat?", "What is one routine I can simplify?", "Which task can I delegate or drop?", "What made me smile in class today?", "What do I want my students to remember from this unit?", "How will I recharge this weekend?", "Which parent message could improve a relationship?", "What do I need help with?"],
    ["I make a difference every day.", "I do not have to do everything.", "Good enough is great.", "My students are growing and so am I.", "Rest makes me a better teacher.", "I choose progress over perfection."],
    ["teacher planner", "lesson plan template", "teacher printable", "classroom organization", "homeschool planner", "weekly lesson planner", "teacher gift", "back to school"],
    ["Multiplication facts practice", "Reading comprehension: main idea", "Fractions on a number line", "Parts of speech sort", "Weather and seasons", "Place value to 1000"],
    ["Too much prep outside school hours", "Tracking grading and parent contact", "Burnout"],
), "teachers", "classroom", "homeschool", "lesson planning")

_add(_n(
    "personal_finance", "Personal Finance", "people who want to budget, save and get out of debt", "clean",
    "Give every dollar a job.",
    ["Bills due this week", "Spending limit", "Money to save", "No-spend goal", "Financial to-do", "Win of the week"],
    ["Tracked spending", "No-spend day", "Saved something", "Checked balance"],
    ["Track every purchase", "Check account balance", "Review upcoming bills", "No-spend day", "Move money to savings", "Pack lunch", "Cancel one unused subscription", "Review weekly budget"],
    ["What does financial freedom look like for me in one year?", "Which expense gives me the most joy per dollar?", "Which subscription could I cancel today?", "What money habit am I proudest of?", "What triggers my impulse spending?", "What would I do with an extra $100 a month?", "What does enough mean to me?", "What is my next money milestone?", "What did I learn about money growing up?", "How will I celebrate paying off a goal?"],
    ["I am in control of my money.", "Every dollar has a purpose.", "Small savings add up.", "I spend on what matters.", "I am building a secure future.", "Debt is temporary; discipline is permanent."],
    ["budget planner", "budget tracker", "debt snowball tracker", "savings challenge", "expense tracker", "monthly budget template", "paycheck budget", "sinking funds"],
    ["Needs vs wants sort", "Build a $1000 emergency fund plan", "Debt snowball steps", "Grocery budget challenge", "Sinking funds setup", "Money goals worksheet"],
    ["Not knowing where money goes", "Budgets that are too rigid", "Irregular income"],
    budget=("Emergency fund", "Debt payoff", "Sinking funds"),
), "budget", "finance", "money", "debt", "savings")

_add(_n(
    "wedding", "Wedding", "engaged couples planning their wedding", "soft",
    "Plan the day, enjoy the journey.",
    ["This week's wedding tasks", "Vendor calls & emails", "Budget check", "Guest list updates", "Inspiration & ideas", "Questions to ask"],
    ["Task done", "Vendor contacted", "Budget logged", "Date night"],
    ["Review one vendor", "Update guest list", "Log wedding spending", "Pin one inspiration idea", "Plan a date night", "Confirm RSVPs", "Check timeline", "Rest and breathe"],
    ["What three words describe the feeling of our wedding day?", "Which moment am I most looking forward to?", "What tradition do we want to keep, and which to skip?", "What will make our guests feel welcome?", "What is a promise I want to make in my vows?", "What do I love most about my partner this week?", "Which decision is stressing me out and what is the next step?", "How can we protect our relationship during planning?", "What detail would make us smile?", "What do we want to remember from this season?"],
    ["We are planning a day that feels like us.", "Everything will come together.", "Love is the point.", "We choose joy over perfection.", "It is okay to ask for help.", "Our marriage matters more than the wedding."],
    ["wedding planner", "wedding checklist", "wedding budget", "wedding timeline", "bride to be", "engagement gift", "wedding printable", "wedding day schedule"],
    ["Guest list tracker", "Vendor comparison", "Wedding day timeline", "Seating chart planner", "Honeymoon budget", "Wedding party gifts"],
    ["Overwhelm from endless decisions", "Budget creep", "Keeping vendors organized"],
), "bride", "wedding planning", "engagement")

_add(_n(
    "student", "Student", "high school and college students", "bold",
    "Study smarter, stress less.",
    ["Assignments due", "Exams & quizzes", "Study blocks", "Reading list", "Group projects", "Weekly reset"],
    ["Class notes", "Study block", "Sleep 7h+", "Exercise"],
    ["Review class notes", "Study block (25 min)", "Plan tomorrow", "Sleep 7 hours", "Drink water", "Move your body", "Phone-free study", "Check deadlines"],
    ["What is the most important deadline this week?", "Which subject needs my freshest energy?", "What study method worked best this week?", "What am I avoiding and why?", "Who can help me with what I do not understand?", "How do I want to feel at the end of this term?", "What distracted me most today?", "What is one habit that helped my grades?", "What would I do if I were not afraid to fail?", "How will I reward myself after exams?"],
    ["I am capable of learning hard things.", "One focused hour beats a distracted evening.", "Mistakes are how I learn.", "I can ask for help.", "Rest helps me remember.", "I am building my future one assignment at a time."],
    ["student planner", "study planner", "college planner", "assignment tracker", "exam study schedule", "gpa tracker", "student printable", "academic planner"],
    ["Study schedule builder", "Exam countdown plan", "Cornell notes practice", "Assignment tracker", "Reading log", "Goal setting for the term"],
    ["Deadlines piling up", "Procrastination", "Exam stress"],
), "college", "university", "study")

_add(_n(
    "nurse", "Nurse", "nurses and nursing students working demanding shifts", "calm",
    "Care for others, plan time to care for you.",
    ["Shift schedule", "Tasks before my shift", "Continuing education", "Errands on days off", "Meal prep", "Self-care plan"],
    ["Hydrate", "Eat a real meal", "Stretch", "Sleep"],
    ["Hydrate on shift", "Eat a real meal", "Stretch feet and back", "Sleep 7 hours", "Decompress after shift", "Meal prep", "Connect with a friend", "Gratitude moment"],
    ["What is one thing I handled well on shift?", "What drained me and what can I do about it?", "Which patient moment will I remember?", "How can I reset between shifts?", "What boundary do I need on days off?", "What am I proud of professionally this month?", "Who can I lean on at work?", "What does a restful day off look like?", "What is one skill I want to build?", "How can I make my commute a decompress ritual?"],
    ["I am enough and I do enough.", "My care matters.", "I protect my own energy.", "Rest is not selfish.", "I grow with every shift.", "I deserve the same care I give."],
    ["nurse planner", "nursing student planner", "shift planner", "nurse gift", "night shift planner", "nurse printable", "nursing school", "self care nurse"],
    ["Shift handoff checklist", "Study plan for NCLEX", "Self-care checklist", "Meal prep plan", "Sleep schedule for night shifts", "Gratitude log"],
    ["Rotating shifts break routines", "Burnout", "Little time for self-care"],
), "nursing", "healthcare", "shift worker")

_add(_n(
    "small_business", "Small Business", "small business owners and solopreneurs", "professional",
    "Run the business before it runs you.",
    ["Revenue goal", "Top 3 business priorities", "Customer follow-ups", "Content & marketing", "Admin & finances", "Win of the week"],
    ["Marketing action", "Follow-up sent", "Money logged", "Break taken"],
    ["Post or send one marketing piece", "Answer customer messages", "Log income and expenses", "Review the pipeline", "Work on one big priority", "Take a real break", "Plan tomorrow", "Learn something"],
    ["What is the one thing that moves my business forward this week?", "Which customer should I thank or follow up with?", "What am I doing that someone else could do?", "What did my best customers have in common?", "What is my next offer or product idea?", "Where is my time actually going?", "What would 10% more revenue require?", "What do I want my business to feel like in a year?", "What is one system I can build this month?", "How will I celebrate this quarter?"],
    ["I run my business with clarity.", "Consistency beats intensity.", "I serve my customers well.", "I price with confidence.", "Progress over perfection.", "I make decisions and move forward."],
    ["small business planner", "business planner", "etsy seller planner", "order tracker", "content planner", "solopreneur", "business goals", "income tracker"],
    ["Business goal setting", "Customer avatar", "Pricing worksheet", "Content calendar starter", "Weekly CEO meeting", "Annual review"],
    ["Wearing every hat", "Inconsistent marketing", "Not tracking numbers"],
    budget=("Software & tools", "Marketing", "Inventory / supplies", "Taxes set-aside"),
), "business", "entrepreneur", "solopreneur", "etsy seller", "freelancer")

_add(_n(
    "fitness", "Fitness", "people building a consistent workout and nutrition routine", "energetic",
    "Show up, track it, repeat.",
    ["Workouts planned", "Meals to prep", "Steps / movement goal", "Water goal", "Sleep goal", "Win of the week"],
    ["Workout", "Water", "Protein", "Sleep"],
    ["Workout or walk", "Drink 2L of water", "Protein at every meal", "Sleep 7-8 hours", "Stretch 5 minutes", "Take progress notes", "Prep tomorrow's meals", "10,000 steps"],
    ["Why do I want to be consistent with fitness?", "Which workout did I enjoy most this week?", "What gets in the way of my routine and how can I plan around it?", "How does my body feel after training?", "What is my next milestone?", "What meal gave me great energy?", "How can I recover better?", "Who can keep me accountable?", "What would a good week look like?", "What am I proud of in my progress?"],
    ["I show up for myself.", "Strong is a feeling, not a number.", "Consistency over intensity.", "My body is capable.", "I enjoy moving.", "Progress is progress."],
    ["fitness planner", "workout tracker", "gym planner", "meal prep planner", "weight loss tracker", "running log", "habit tracker fitness", "health planner"],
    ["Weekly workout planner", "Meal prep list", "Water tracker", "Body measurements log", "Goal setting for the month", "Recovery checklist"],
    ["Losing motivation after two weeks", "Not tracking progress", "No time"],
), "workout", "gym", "health", "weight loss")

_add(_n(
    "mindfulness", "Mindfulness", "people who want calm, gratitude and a gentle daily reflection routine", "calm",
    "A little quiet, every day.",
    ["Intention for the week", "Moments of calm", "Gratitude", "Letting go", "Self-care plan", "Reflection"],
    ["Breathe", "Gratitude", "Unplug", "Kindness"],
    ["5-minute morning pause", "Gratitude moment", "Mindful walk", "Screen-free hour", "Evening reflection", "Deep breaths x5", "Kind act", "Early bedtime"],
    ["What am I grateful for right now?", "What is weighing on me that I can set down?", "How does my body feel today?", "What would I tell a friend in my situation?", "What brought me peace this week?", "What does rest look like for me?", "Which thought do I want to let go of?", "What is one gentle thing I can do for myself?", "What small moment did I almost miss?", "What do I need more of, and less of?"],
    ["I am present in this moment.", "I release what I cannot control.", "Calm is available to me.", "I am worthy of rest.", "I choose peace.", "I breathe and begin again."],
    ["gratitude journal", "mindfulness journal", "self care planner", "daily reflection", "guided journal", "anxiety journal", "wellness planner", "journal prompts"],
    ["Breathing practice log", "Gratitude list", "Worry vs control sort", "Body scan check-in", "Self-compassion letter", "Weekly reflection"],
    ["Overthinking", "Never taking time for yourself", "Stress"],
), "journal", "journaling", "gratitude", "self care", "wellness", "anxiety")

_add(_n(
    "new_mom", "New Mom", "new parents navigating baby's first year", "soft",
    "Gentle structure for the sleepy season.",
    ["Baby schedule notes", "Appointments", "Meals & groceries", "Help I need", "Time for me", "Milestones & memories"],
    ["Feeds", "Naps", "Water", "Rest"],
    ["Drink water", "Eat something warm", "Step outside", "Rest when baby rests", "Ask for help", "Take a photo", "Check in with partner", "5 minutes just for me"],
    ["What was the sweetest moment today?", "What am I doing better than I give myself credit for?", "What help do I need and who can I ask?", "What would make tomorrow a little easier?", "How am I really feeling?", "What do I want to remember about this stage?", "What is one thing I can let go of?", "What does my partner and I need this week?", "What is baby learning right now?", "How can I rest today?"],
    ["I am a good parent.", "This season is temporary.", "I am allowed to ask for help.", "Rest is productive.", "I am learning as I go.", "I am enough for my baby."],
    ["new mom planner", "baby tracker", "postpartum planner", "baby journal", "mom printable", "baby shower gift", "feeding log", "sleep tracker baby"],
    ["Newborn schedule log", "Hospital bag checklist", "Feeding & diaper tracker", "Postpartum self-care", "First-year milestones", "Meal train planner"],
    ["Sleep deprivation", "Mental load", "No time for self-care"],
), "mom", "mother", "baby", "postpartum", "parenting")

_add(_n(
    "pet_owner", "Pet Owner", "dog and cat owners who love organizing their pet's life", "warm",
    "Everything your best friend needs, in one place.",
    ["Vet & grooming", "Meals & meds", "Walks / playtime", "Training goal", "Supplies to buy", "Cute moments"],
    ["Walk", "Meds", "Training", "Play"],
    ["Morning walk", "Fresh water", "Meds / supplements", "Training 5 minutes", "Play session", "Brush or groom", "Clean bowls", "Cuddle time"],
    ["What new thing did my pet learn?", "What made my pet happiest this week?", "What do I want to teach next?", "Which health notes should I tell the vet?", "What is my pet's favourite routine?", "How can I enrich my pet's day?", "What memory do I want to keep?", "What did my pet teach me?", "What supplies are running low?", "How is my pet's energy and appetite?"],
    ["I give my pet the best life.", "Patience builds trust.", "Every day is a good day for a walk.", "I am my pet's favourite human.", "Small routines matter.", "Love is the best treat."],
    ["pet planner", "dog planner", "pet care tracker", "dog training log", "cat care", "puppy tracker", "pet health record", "pet printable"],
    ["Vet visit log", "Puppy training tracker", "Feeding schedule", "Pet expense tracker", "Vaccination record", "Walk log"],
    ["Forgetting vet dates and meds", "Tracking training progress", "Pet expenses"],
    budget=("Pet food", "Vet & medication", "Grooming", "Toys & supplies"),
), "dog", "cat", "pets", "puppy")

_add(_n(
    "gardening", "Gardening", "home gardeners and allotment growers", "earthy",
    "Plan what you plant, enjoy what you grow.",
    ["Sow / plant this week", "Water & feed", "Harvest", "Pests & problems", "Seeds & supplies", "Garden notes"],
    ["Water", "Weed", "Check pests", "Harvest"],
    ["Water plants", "Check for pests", "Weed 10 minutes", "Harvest", "Compost kitchen scraps", "Record garden notes", "Start seeds", "Enjoy the garden"],
    ["What is thriving in my garden right now?", "What failed and what will I try instead?", "What do I want to grow next season?", "Which task will save me time next month?", "What did the weather teach me this week?", "What is my favourite harvest so far?", "How can I attract more pollinators?", "What do I want my garden to feel like?", "What are my soil notes?", "What am I proud of in the garden?"],
    ["I grow patiently.", "Every season teaches me something.", "My garden is a place of calm.", "Small seeds become big harvests.", "I learn from each season.", "I nurture what I plant."],
    ["garden planner", "gardening journal", "planting calendar", "seed starting log", "vegetable garden planner", "garden gift", "harvest tracker", "garden printable"],
    ["Seed starting schedule", "Garden layout planner", "Harvest log", "Companion planting guide", "Pest log", "Seasonal task list"],
    ["Forgetting when to plant", "Tracking what worked", "Pests and problems"],
), "garden", "plants", "houseplants")

_add(_n(
    "faith", "Faith & Devotion", "Christians who want a consistent prayer and scripture habit", "calm",
    "Make space for what matters most.",
    ["Scripture focus", "Prayer requests", "Gratitude", "Serving others", "Sermon notes", "Praise reports"],
    ["Scripture", "Prayer", "Gratitude", "Serve"],
    ["Read scripture", "Pray", "Gratitude list", "Serve someone", "Memorize a verse", "Worship", "Sabbath rest", "Evening prayer"],
    ["What did God show me in scripture today?", "Who can I pray for this week?", "Where have I seen answered prayer?", "What am I holding on to that I need to give to God?", "How can I serve someone this week?", "What verse do I want to carry today?", "What am I thankful for?", "What does rest in God look like for me?", "What is one step of obedience for me?", "What do I want to remember from this sermon?"],
    ["I am loved and held.", "God is with me in every season.", "His mercies are new every morning.", "I trust the plan.", "I am grateful.", "I walk in peace."],
    ["prayer journal", "bible study planner", "devotional journal", "christian planner", "scripture journal", "gratitude prayer", "faith printable", "sermon notes"],
    ["Prayer request tracker", "Scripture memory", "Gratitude and praise", "Sermon notes", "Weekly Sabbath plan", "Serving plan"],
    ["Inconsistent quiet time", "Forgetting prayer requests", "Distractions"],
), "christian", "prayer", "bible", "devotional", "church")

_add(_n(
    "home", "Home Organization", "people who want a tidy, calm, organized home", "fresh",
    "A calmer home, one small reset at a time.",
    ["Daily 15-minute reset", "Zone of the week", "Laundry plan", "Meals & groceries", "Errands", "Declutter goal"],
    ["Dishes", "Laundry", "Tidy", "Trash"],
    ["Make the bed", "Dishes done", "Laundry load", "10-minute tidy", "Wipe surfaces", "Reset entryway", "Take out trash", "Prep tomorrow"],
    ["Which space bothers me most and what is one small fix?", "What routine would make my mornings smoother?", "What am I keeping that I no longer need?", "Which zone should I reset this week?", "How do I want my home to feel?", "What chore can I make easier?", "Who can share the load?", "What did I finish that I am proud of?", "What is one habit that keeps my home calm?", "What can I donate this week?"],
    ["My home supports me.", "Small resets add up.", "I do not need to be perfect.", "I can let things go.", "A calm home, a calm mind.", "I keep it simple."],
    ["cleaning planner", "home organization", "chore chart", "cleaning schedule", "declutter checklist", "household planner", "weekly reset", "home management binder"],
    ["Weekly cleaning schedule", "Declutter checklist", "Meal plan and grocery list", "Chore chart", "Home maintenance log", "Monthly reset"],
    ["Overwhelming mess", "Unequal chores", "No routine"],
), "home organization", "cleaning", "declutter", "household", "chore")

_add(_n(
    "meal_planning", "Meal Planning", "people who want to plan meals, save money and reduce food waste", "fresh",
    "Plan once, eat well all week.",
    ["Meals this week", "Grocery list", "Prep list", "Pantry check", "Budget", "Recipe ideas"],
    ["Breakfast", "Lunch", "Dinner", "Snack"],
    ["Check pantry before shopping", "Prep one ingredient", "Cook once, eat twice", "Use leftovers", "Pack lunch", "Drink water", "Try a new recipe", "Update grocery list"],
    ["Which meals did my family love this week?", "What did I waste and how can I prevent it?", "What new recipe do I want to try?", "How can I save time on weeknights?", "What is my favourite batch recipe?", "What is in my pantry I forgot about?", "Which meal was the cheapest and best?", "What would make cooking easier?", "What do I want to eat more of?", "How can I use leftovers creatively?"],
    ["Cooking is care.", "Planning gives me freedom.", "I nourish my body.", "Simple meals are enough.", "I waste less and enjoy more.", "I make time for good food."],
    ["meal planner", "weekly meal plan", "grocery list", "meal prep planner", "menu planner", "budget meal plan", "recipe tracker", "pantry inventory"],
    ["Weekly menu plan", "Grocery list by aisle", "Pantry inventory", "Batch cooking plan", "Recipe card", "Budget grocery challenge"],
    ["Daily 'what's for dinner' stress", "Food waste", "Grocery overspending"],
    budget=("Groceries", "Dining out", "Meal delivery"),
), "meal prep", "menu planning", "grocery", "recipes", "cooking")


def resolve_niche(text: str) -> NicheProfile:
    """Map free text to a library niche (exact, alias, or word overlap), else build a generic profile."""
    t = text.strip().lower()
    if t in ALIASES:
        return LIBRARY[ALIASES[t]]
    words = set(re.findall(r"[a-z]+", t))
    best, score = None, 0
    for alias, key in ALIASES.items():
        aw = set(re.findall(r"[a-z]+", alias))
        s = len(words & aw)
        if s > score and aw <= words | {"planner"}:
            best, score = key, s
    if best and score:
        return LIBRARY[best]
    return generic_profile(text)


def generic_profile(text: str) -> NicheProfile:
    name = text.strip().title() or "Productivity"
    return NicheProfile(
        key=re.sub(r"[^a-z0-9]+", "_", text.strip().lower()).strip("_") or "general",
        name=name,
        audience=f"people interested in {text.strip().lower() or 'getting organized'}",
        mood="calm",
        tagline=f"Plan it. Track it. Enjoy {name.lower()}.",
        weekly_boxes=["Top 3 priorities", "Appointments & deadlines", "To do this week", "Ideas & notes", "Small wins", "Looking ahead"],
        daily_labels=["Priority done", "Move", "Water", "Rest"],
        habits=["Plan the day", "Drink water", "Move your body", "Read or learn", "Tidy for 10 minutes", "Reflect for 5 minutes", "Early bedtime", "Do one thing for future you"],
        prompts=[
            f"What does success in {text.strip().lower() or 'this area'} look like for me this month?",
            f"What is the biggest obstacle in {text.strip().lower() or 'this area'} right now?",
            "What is one small step I can take today?",
            "What did I learn this week?",
            "Who can support me?",
            "What am I proud of?",
            "What should I stop doing?",
            "What do I want more of?",
        ],
        affirmations=["I make steady progress.", "I choose what matters.", "Small steps add up.", "I learn from every attempt.", "I am building good habits.", "I can do this."],
        seo_keywords=[f"{text.strip().lower()} planner", f"{text.strip().lower()} printable", f"{text.strip().lower()} tracker", "undated planner", "digital download"],
        worksheet_topics=["Goal setting", "Weekly review", "Habit builder", "Idea capture", "Progress check-in", "Monthly reset"],
        pain_points=["Not knowing where to start", "Staying consistent", "Tracking progress"],
    )


def library_keys() -> list[str]:
    return sorted(LIBRARY)


def niche_to_dict(n: NicheProfile) -> dict[str, Any]:
    return n.model_dump()
