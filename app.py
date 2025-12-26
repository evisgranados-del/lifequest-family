import streamlit as st
import datetime
import json
import os
import pandas as pd
import time
import random
from io import StringIO

# --- CONFIGURATION ---
st.set_page_config(page_title="LifeQuest: Family Guild", page_icon="🛡️", layout="wide")
SAVE_FILE = "save_data.json"

# --- VISUAL STYLING ---
def local_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Orbitron', sans-serif;
        }
        h1, h2, h3 {
            color: #4da6ff !important;
            text-shadow: 0 0 5px #4da6ff;
        }
        .stProgress > div > div > div > div {
            background-color: #4da6ff;
        }
        /* XP Bar is Yellow */
        .xp-bar .stProgress > div > div > div > div {
            background-color: #ffd700;
        }
        [data-testid="stVerticalBlock"] > [style*="flex-direction: column;"] > [data-testid="stVerticalBlock"] {
            border: 1px solid #333;
            border-radius: 10px;
            background-color: #0e1117;
            box-shadow: 0 0 10px rgba(0,0,0,0.5);
        }
        .stButton>button {
            border: 1px solid #4da6ff;
            color: #4da6ff;
            background-color: transparent;
            transition: all 0.3s ease;
        }
        .stButton>button:hover {
            background-color: #4da6ff;
            color: white;
            box-shadow: 0 0 10px #4da6ff;
        }
        /* Late Task Warning */
        .late-task {
            color: #ff4b4b;
            font-weight: bold;
        }
        .due-today {
            color: #ffa500;
            font-weight: bold;
        }
        [data-testid="stSidebar"] img {
            border-radius: 10px;
            box-shadow: 0 0 15px #4da6ff;
        }
    </style>
    """, unsafe_allow_html=True)

# --- EVOLUTION MAPPINGS ---
ROLE_PREFIXES = {
    "👨‍✈️ Dad (Monarch)": "dad",
    "👩‍⚕️ Mom (Healer)": "mom",
    "🔮 Daughter (15) (Caster)": "daughter",
    "🛡️ Son (10) (Tank)": "son"
}

RANK_SUFFIXES = {
    "E-Rank": "rank_e", "D-Rank": "rank_d", "C-Rank": "rank_c",
    "B-Rank": "rank_b", "A-Rank": "rank_a", "S-Rank": "rank_s", "Nation-Level": "rank_nation"
}

RANKS = {
    0: "E-Rank", 1000: "D-Rank", 2500: "C-Rank", 5000: "B-Rank",
    10000: "A-Rank", 20000: "S-Rank", 50000: "Nation-Level"
}

# --- FAMILY ARCHETYPES ---
FAMILY_TEMPLATES = {
    "👨‍✈️ Dad (Monarch)": {
        "shop": {"🥤 Cheat Meal": 150, "🎮 1hr Gaming": 100, "🎬 Pick Movie": 300, "💤 1hr Nap": 50},
        "habits": {
            "⚔️ Iron Prayer (Gym)": ["Strength", None], 
            "🥩 Paleo Diet": ["Vitality", None],
            "👑 Legacy Time": ["Spirit", None],
            "💧 Gallon Water": ["Vitality", None]
        }
    },
    "👩‍⚕️ Mom (Healer)": {
        "shop": {"☕ Starbucks Run": 100, "🛁 Spa Hour": 100, "🍷 Wine": 50, "📖 Reading Time": 100},
        "habits": {
            "✨ Mana Regen (Yoga)": ["Agility", None], 
            "🥗 Potion Brewing (Health)": ["Vitality", None],
            "💧 Elixir (Water)": ["Vitality", None],
            "💖 Self Healing": ["Spirit", None]
        }
    },
    "🔮 Daughter (15) (Caster)": {
        "shop": {"🚗 Gas Money ($10)": 500, "💄 Makeup Item": 400, "📱 +1 Hr Phone": 50, "⏰ Curfew +1hr": 200},
        "habits": {
            "⚡ Swift Cleanse (Dishes)": ["Agility", None],
            "📚 Arcane Focus (HW On Time)": ["Intellect", None],
            "🎷 Bardic Training (Band)": ["Spirit", None],
            "🏃‍♀️ Battle Ready (Sports)": ["Strength", None]
        }
    },
    "🛡️ Son (10) (Tank)": {
        "shop": {"🎮 1 Hr Gaming": 50, "💵 $10 Robux": 400, "🍦 Ice Cream": 100, "🛌 Late Night (1hr)": 150},
        "habits": {
            "🛡️ Fortify Base (Chores)": ["Spirit", None],
            "🥩 Rations (Clean Eat)": ["Vitality", None],
            "🎷 War Drums (Band)": ["Intellect", None],
            "🏋️ Training Arc (Gym)": ["Strength", None]
        }
    }
}

DEFAULT_SKILLS = {
    "🛡️ Guardian (Safety)": {
        "Situational Awareness": {"status": "In Progress", "attr": "Sense", "xp": 50},
        "Self Defense Basics": {"status": "In Progress", "attr": "Strength", "xp": 100}
    },
    "💰 Merchant (Finance)": {
        "Budgeting/Saving": {"status": "In Progress", "attr": "Sense", "xp": 50},
        "Compound Interest": {"status": "In Progress", "attr": "Intellect", "xp": 75}
    },
    "🔧 Artificer (Mechanics)": {
        "Change Flat Tire": {"status": "In Progress", "attr": "Strength", "xp": 100},
        "Check Oil/Fluids": {"status": "In Progress", "attr": "Sense", "xp": 50}
    },
    "🔥 Survivalist (Outdoors)": {
        "Knot Tying": {"status": "In Progress", "attr": "Agility", "xp": 50},
        "Start Fire (No Match)": {"status": "In Progress", "attr": "Sense", "xp": 100}
    }
}

# --- DATA PERSISTENCE ---
def load_all_data():
    if os.path.exists(SAVE_FILE):
        with open(SAVE_FILE, "r") as f:
            return json.load(f)
    return {}

def init_user_data(username):
    template = FAMILY_TEMPLATES.get(username, FAMILY_TEMPLATES["👨‍✈️ Dad (Monarch)"])
    return {
        "xp": {"Strength": 0, "Intellect": 0, "Vitality": 0, "Agility": 0, "Sense": 0, "Spirit": 0},
        "attributes": {"HP": 100, "Max_HP": 100, "Gold": 0},
        "habits": template["habits"],
        "shop": template["shop"],
        "one_time_tasks": [],
        "completed_history": [],
        "skills": DEFAULT_SKILLS, 
        "workout_queue": {},
        "active_workout": None,
        "workout_history": [],
        "inventory": [],
        "weight_log": {"dates": [], "weights": []},
        "last_login": str(datetime.date.today())
    }

def save_current_user(username):
    all_data = load_all_data()
    user_keys = init_user_data("temp").keys()
    user_data = {k: v for k, v in st.session_state.items() if k in user_keys}
    all_data[username] = user_data
    with open(SAVE_FILE, "w") as f:
        json.dump(all_data, f)

def admin_save_target_user(target_username, target_data):
    all_data = load_all_data()
    all_data[target_username] = target_data
    with open(SAVE_FILE, "w") as f:
        json.dump(all_data, f)

# --- VISUALS ---
local_css()

# --- LOGIN SCREEN ---
st.sidebar.title("🏰 The Guild Hall")
all_data = load_all_data()
user_list = list(FAMILY_TEMPLATES.keys())
selected_user = st.sidebar.selectbox("Select Character:", user_list)

if 'current_user' not in st.session_state or st.session_state.current_user != selected_user:
    st.session_state.current_user = selected_user
    user_data = all_data.get(selected_user, init_user_data(selected_user))
    # Migration checks
    if "shop" not in user_data: user_data["shop"] = FAMILY_TEMPLATES[selected_user]["shop"]
    if "attributes" in user_data and "Gold" not in user_data["attributes"]: user_data["attributes"]["Gold"] = 0
    
    for k, v in user_data.items():
        st.session_state[k] = v
    st.rerun()

# --- HELPER FUNCTIONS ---
def get_rank(total_xp):
    current_rank = "E-Rank"
    for threshold, title in RANKS.items():
        if total_xp >= threshold:
            current_rank = title
    return current_rank

def check_level_up(category, old_xp, new_xp):
    if (new_xp // 100) > (old_xp // 100):
        st.balloons()
        st.session_state.attributes["Gold"] += 100
        st.session_state.attributes["HP"] = st.session_state.attributes["Max_HP"]
        st.toast(f"🏆 LEVEL UP! {category} increased!", icon="🔥")
        st.toast(f"💰 BONUS: +100 Gold", icon="🪙")
        st.toast("❤️ HP Restored!", icon="✨")

def apply_daily_penalty():
    today = str(datetime.date.today())
    last = st.session_state.last_login
    if today != last:
        yesterday_obj = datetime.date.today() - datetime.timedelta(days=1)
        yesterday_str = yesterday_obj.isoformat()
        missed_count = 0
        for habit, data in st.session_state.habits.items():
            last_done = data[1]
            if last_done != yesterday_str and last_done != today:
                missed_count += 1
        if missed_count > 0:
            damage = missed_count * 10
            st.session_state.attributes["HP"] -= damage
            st.toast(f"☠️ PENALTY: You missed {missed_count} Daily Quests! -{damage} HP", icon="🩸")
            if st.session_state.attributes["HP"] <= 0:
                st.session_state.attributes["HP"] = 1 
                st.error("⚠️ SYSTEM WARNING: CRITICAL STATE.")
        st.session_state.last_login = today
        save_current_user(st.session_state.current_user)

apply_daily_penalty()

# --- GYM HELPERS ---
def calculate_plates(target_weight):
    try: target = float(target_weight)
    except: return "Enter a valid number"
    if target < 45: return "Weight must be >= 45 (Bar)"
    weight_per_side = (target - 45) / 2
    inventory = {45: 2, 35: 2, 25: 2, 15: 2, 10: 4, 5: 2, 2.5: 2}
    plates_needed = []
    for plate in sorted(inventory.keys(), reverse=True):
        while weight_per_side >= plate and inventory[plate] >= 2:
            plates_needed.append(str(plate))
            weight_per_side -= plate
            inventory[plate] -= 2
    if weight_per_side > 0: return f"Load: {', '.join(plates_needed)} + {weight_per_side} lbs remainder"
    if not plates_needed: return "Bar Only"
    return f"Per Side: [{' | '.join(plates_needed)}]"

def parse_csv_workout(csv_text):
    try:
        df = pd.read_csv(StringIO(csv_text))
        df.columns = [c.strip().lower() for c in df.columns]
        required = ['day', 'exercise', 'sets', 'reps']
        if not all(col in df.columns for col in required): return None, "Error: CSV must have columns: Day, Exercise, Sets, Reps"
        weekly_plan = {}
        for day_name, group in df.groupby('day'):
            exercises = []
            for _, row in group.iterrows():
                exercises.append({
                    "name": row['exercise'], "sets": str(row['sets']), "reps": str(row['reps']),
                    "trainer_note": row.get('notes', ''), "my_weight": "", "my_notes": "", "sets_completed": 0
                })
            weekly_plan[day_name] = exercises
        return weekly_plan, f"Loaded {len(weekly_plan)} days of missions!"
    except Exception as e: return None, f"CSV Error: {e}"

def extract_time(reps_str):
    reps_str = reps_str.lower()
    if 's' in reps_str or 'sec' in reps_str:
        import re
        num = re.findall(r'\d+', reps_str)
        return int(num[0]) if num else 0
    elif 'min' in reps_str:
        import re
        num = re.findall(r'\d+', reps_str)
        return int(num[0]) * 60 if num else 0
    return 0

def get_previous_log(exercise_name):
    if st.session_state.workout_history:
        for session in reversed(st.session_state.workout_history):
            if "exercises" in session:
                for ex in session["exercises"]:
                    if exercise_name.lower().strip() == ex["name"].lower().strip():
                        if ex.get("my_weight") or ex.get("my_notes"):
                            return ex.get("my_weight", "N/A"), ex.get("my_notes", "No notes")
    return None, None

# --- NAVIGATION ---
menu_options = ["🏠 Dashboard", "🔥 Quest Board", "💰 Market", "🎒 Inventory", "🌳 Legacy Skills", "🏋️ Gym", "📜 History"]
is_admin = "Dad" in st.session_state.current_user or "Mom" in st.session_state.current_user
if is_admin:
    menu_options.append("👑 Admin Panel")

menu = st.sidebar.radio("MENU", menu_options)

# --- SIDEBAR DISPLAY ---
st.sidebar.divider()
total_xp = sum(st.session_state.xp.values())
player_level = total_xp // 100 + 1
rank_title = get_rank(total_xp)

prefix = ROLE_PREFIXES.get(st.session_state.current_user, "dad")
suffix = RANK_SUFFIXES.get(rank_title, "rank_e")
image_file = f"{prefix}_{suffix}.png"
image_path = os.path.join("assets", image_file)

if os.path.exists(image_path):
    st.sidebar.image(image_path, caption=f"{st.session_state.current_user}")
else:
    fallback = os.path.join("assets", f"{prefix}_rank_e.png")
    if os.path.exists(fallback):
        st.sidebar.image(fallback, caption=f"{st.session_state.current_user}")
    else:
        st.sidebar.warning(f"⚠️ Missing: {image_file}")

hp = st.session_state.attributes["HP"]
max_hp = st.session_state.attributes["Max_HP"]
gold = st.session_state.attributes.get("Gold", 0)

st.sidebar.write(f"❤️ **HP: {hp}/{max_hp}**")
st.sidebar.progress(hp / max_hp)
st.sidebar.write(f"🪙 **Gold: {gold} GP**")

st.sidebar.markdown(f"<small>⚡ <b>XP to Next Level</b></small>", unsafe_allow_html=True)
st.sidebar.markdown('<div class="xp-bar">', unsafe_allow_html=True)
st.sidebar.progress((total_xp % 100) / 100)
st.sidebar.markdown('</div>', unsafe_allow_html=True)

st.sidebar.divider()
cols = st.sidebar.columns(2)
for i, (stat, val) in enumerate(st.session_state.xp.items()):
    stat_lvl = val // 100 + 1
    stat_prog = (val % 100) / 100
    with cols[i % 2]:
        st.markdown(f"<div style='font-size: 0.8rem;'><b>{stat}</b> Lv.{stat_lvl}</div>", unsafe_allow_html=True)
        st.progress(stat_prog)

# =========================================================
#  ZONE 1: DASHBOARD
# =========================================================
if menu == "🏠 Dashboard":
    st.title(f"Hello, {st.session_state.current_user.split()[1]}!")
    c1, c2, c3 = st.columns(3)
    c1.metric("Gold Coins", f"{gold} GP")
    c2.metric("Loot Bags", len(st.session_state.inventory))
    c3.metric("Total XP", total_xp)
    st.divider()
    
    st.subheader("🏆 Guild Leaderboard")
    leaderboard = []
    for user, data in all_data.items():
        xp = sum(data["xp"].values())
        u_gold = data["attributes"].get("Gold", 0)
        rank = get_rank(xp)
        leaderboard.append({"User": user, "Rank": rank, "Gold": u_gold, "Total XP": xp})
    if leaderboard:
        st.dataframe(pd.DataFrame(leaderboard).sort_values("Total XP", ascending=False), use_container_width=True)
        
    st.divider()
    if "Dad" in st.session_state.current_user or "Son" in st.session_state.current_user:
        st.subheader("⚖️ Body Mass Tracker")
        c_chart, c_input = st.columns([3, 1])
        with c_input:
            with st.form("weight_in"):
                w_in = st.number_input("Current Weight (lbs)", min_value=0.0, step=0.1)
                if st.form_submit_button("Log Weigh-In"):
                    st.session_state.weight_log["dates"].append(str(datetime.date.today()))
                    st.session_state.weight_log["weights"].append(w_in)
                    save_current_user(st.session_state.current_user)
                    st.toast("Weight Logged!", icon="⚖️")
                    st.rerun()
        with c_chart:
            if st.session_state.weight_log["weights"]:
                df_weight = pd.DataFrame({"Date": st.session_state.weight_log["dates"], "Weight": st.session_state.weight_log["weights"]})
                st.line_chart(df_weight.set_index("Date"))
            else: st.info("Log your weight to see the chart.")

# =========================================================
#  ZONE 2: QUEST BOARD (UPDATED WITH DUE DATES)
# =========================================================
elif menu == "🔥 Quest Board":
    st.title("⚡ Daily Quests")
    
    st.subheader("🔁 Habits (+5 Gold)")
    if st.session_state.habits:
        cols = st.columns(3)
        for i, (habit, data) in enumerate(st.session_state.habits.items()):
            stat, last_done = data[0], data[1]
            is_done = last_done == datetime.date.today().isoformat()
            with cols[i % 3]:
                with st.container(border=True):
                    st.markdown(f"**{habit}**")
                    st.caption(f"+15 {stat} | +5 GP")
                    if st.button(f"{'✅ Done' if is_done else '⭕ Do It'}", key=habit, use_container_width=True, disabled=is_done):
                        if not is_done:
                            st.session_state.habits[habit][1] = datetime.date.today().isoformat()
                            old_xp = st.session_state.xp[stat]
                            st.session_state.xp[stat] += 15
                            st.session_state.attributes["Gold"] += 5
                            st.session_state.completed_history.append(f"{datetime.date.today()} - {habit} (+5 GP)")
                            check_level_up(stat, old_xp, st.session_state.xp[stat])
                            save_current_user(st.session_state.current_user)
                            st.rerun()

    st.subheader("📜 Assigned Tasks (Check Due Dates)")
    if not st.session_state.one_time_tasks:
        st.info("No active tasks.")
    
    for i, task in enumerate(st.session_state.one_time_tasks):
        if not task["done"]:
            # Due Date Logic
            due_str = task.get("due_date", str(datetime.date.today()))
            due_date = datetime.datetime.strptime(due_str, "%Y-%m-%d").date()
            today = datetime.date.today()
            
            # Label
            label = f"⬜ {task['name']}"
            note = f"+40 {task['stat']}"
            gold_reward = 25
            
            if due_date < today:
                label += " (LATE)"
                note += " | 🚨 OVERDUE (-15 GP Penalty)"
                gold_reward = 10 # Late penalty
                color_class = "late-task"
            elif due_date == today:
                label += " (DUE TODAY)"
                note += " | ⚠️ Due Today!"
                color_class = "due-today"
            else:
                note += f" | 📅 Due: {due_str}"
                color_class = "normal"

            if st.button(f"{label} \n {note}", key=f"ot_{i}", use_container_width=True):
                st.session_state.one_time_tasks[i]["done"] = True
                old_xp = st.session_state.xp[task['stat']]
                st.session_state.xp[task['stat']] += 40
                st.session_state.attributes["Gold"] += gold_reward
                
                status_msg = "LATE" if gold_reward == 10 else "ON TIME"
                st.session_state.completed_history.append(f"{datetime.date.today()} - Task: {task['name']} ({status_msg}) (+{gold_reward} GP)")
                
                check_level_up(task['stat'], old_xp, st.session_state.xp[task['stat']])
                save_current_user(st.session_state.current_user)
                st.rerun()

# =========================================================
#  ZONE 3: MARKET
# =========================================================
elif menu == "💰 Market":
    st.title("💰 The Goblin Market")
    st.caption(f"Current Balance: {gold} GP")
    
    if st.session_state.shop:
        cols = st.columns(3)
        for i, (item, price) in enumerate(st.session_state.shop.items()):
            with cols[i % 3]:
                with st.container(border=True):
                    st.markdown(f"**{item}**")
                    st.markdown(f"🪙 **{price} GP**")
                    if gold >= price:
                        if st.button(f"Buy", key=f"buy_{i}"):
                            st.session_state.attributes["Gold"] -= price
                            st.session_state.inventory.append(item)
                            st.toast(f"Purchased {item}!", icon="🛍️")
                            st.session_state.completed_history.append(f"{datetime.date.today()} - Bought {item} (-{price} GP)")
                            save_current_user(st.session_state.current_user)
                            st.rerun()
                    else:
                        st.button(f"Need {price-gold} more", key=f"no_{i}", disabled=True)
    else:
        st.info("Market is closed.")

# =========================================================
#  ZONE 4: INVENTORY
# =========================================================
elif menu == "🎒 Inventory":
    st.title("🎒 My Loot")
    if not st.session_state.inventory:
        st.info("No items purchased.")
    else:
        for i, item in enumerate(st.session_state.inventory):
            c1, c2 = st.columns([3, 1])
            c1.success(f"📦 {item}")
            if c2.button("Redeem / Use", key=f"use_{i}"):
                st.session_state.inventory.pop(i)
                st.toast(f"Redeemed: {item}!", icon="✅")
                save_current_user(st.session_state.current_user)
                st.rerun()

# =========================================================
#  ZONE 5: LEGACY SKILLS
# =========================================================
elif menu == "🌳 Legacy Skills":
    st.title("🌳 Skill Tree")
    
    # Only Admin adds skills
    if is_admin:
        with st.expander("➕ Add Custom Skill (Admin Only)"):
            c1, c2 = st.columns(2)
            new_cat = c1.selectbox("Category", list(st.session_state.skills.keys()))
            new_name = c2.text_input("Skill Name")
            c3, c4 = st.columns(2)
            new_attr = c3.selectbox("Attribute Reward", list(st.session_state.xp.keys()))
            new_xp = c4.number_input("XP Amount", value=50, step=10)
            if st.button("Create Skill"):
                if new_name:
                    st.session_state.skills[new_cat][new_name] = {"status": "In Progress", "attr": new_attr, "xp": new_xp}
                    save_current_user(st.session_state.current_user)
                    st.success(f"Added {new_name}!")
                    st.rerun()
        st.divider()

    tabs = st.tabs(list(st.session_state.skills.keys()))
    for i, cat in enumerate(st.session_state.skills.keys()):
        with tabs[i]:
            for skill_name, skill_data in st.session_state.skills[cat].items():
                if isinstance(skill_data, dict):
                    status = skill_data.get("status", "In Progress")
                    attr = skill_data.get("attr", "Intellect")
                    xp_val = skill_data.get("xp", 50)
                else: status, attr, xp_val = skill_data, "Intellect", 50

                c1, c2 = st.columns([3, 1])
                if status == "Mastered":
                    c1.success(f"🏆 {skill_name} (Mastered)")
                else:
                    c1.info(f"✨ {skill_name} (+{xp_val} {attr})")
                
                if status != "Mastered":
                    if c2.button("Master", key=f"master_{skill_name}"):
                        if isinstance(skill_data, dict): st.session_state.skills[cat][skill_name]["status"] = "Mastered"
                        else: st.session_state.skills[cat][skill_name] = "Mastered"
                        
                        old_val = st.session_state.xp[attr]
                        st.session_state.xp[attr] += xp_val
                        st.session_state.completed_history.append(f"{datetime.date.today()} - Mastered: {skill_name}")
                        check_level_up(attr, old_val, st.session_state.xp[attr])
                        save_current_user(st.session_state.current_user)
                        st.balloons()
                        st.rerun()

# =========================================================
#  ZONE 6: GYM
# =========================================================
elif menu == "🏋️ Gym":
    st.title("⛓️ The Dungeon")
    if not st.session_state.active_workout:
        with st.expander("Import CSV Workout"):
             csv_input = st.text_area("CSV Data")
             if st.button("Load"):
                 plan, msg = parse_csv_workout(csv_input)
                 if plan:
                     st.session_state.workout_queue = plan
                     save_current_user(st.session_state.current_user)
                     st.rerun()
        if st.session_state.workout_queue:
            day_opt = list(st.session_state.workout_queue.keys())
            sel_day = st.selectbox("Select Workout", day_opt)
            if st.button("Start Workout"):
                st.session_state.active_workout = {
                    "date": datetime.date.today().isoformat(),
                    "day_name": sel_day,
                    "exercises": st.session_state.workout_queue[sel_day],
                    "current_step": 0
                }
                save_current_user(st.session_state.current_user)
                st.rerun()
    else:
        workout = st.session_state.active_workout
        step = workout["current_step"]
        total = len(workout["exercises"])
        st.progress((step)/total)
        if step >= total:
            st.success("🎉 DUNGEON CLEARED!")
            if st.button("Claim Rewards & Exit"):
                old_xp = st.session_state.xp["Strength"]
                st.session_state.xp["Strength"] += 150
                st.session_state.xp["Agility"] += 50
                st.session_state.attributes["Gold"] += 50
                st.session_state.completed_history.append(f"{datetime.date.today()} - Cleared Dungeon (+200 XP | +50 GP)")
                st.session_state.workout_history.append(workout)
                del st.session_state.workout_queue[workout["day_name"]]
                st.session_state.active_workout = None
                check_level_up("Strength", old_xp, st.session_state.xp["Strength"])
                save_current_user(st.session_state.current_user)
                st.rerun()
        else:
            ex = workout["exercises"][step]
            st.markdown(f"## ⚔️ {ex['name']}")
            prev_w, prev_n = get_previous_log(ex['name'])
            if prev_w: st.info(f"Last: {prev_w} | {prev_n}")
            with st.expander("🧮 Plate Calc"):
                target = st.number_input("Target", value=135, step=5)
                st.code(calculate_plates(target))
            c1, c2 = st.columns(2)
            c1.metric("Sets", ex['sets'])
            c2.metric("Reps", ex['reps'])
            try: num_sets = int(str(ex['sets']).split('-')[0])
            except: num_sets = 3
            cols = st.columns(num_sets)
            for i in range(num_sets):
                if i < ex['sets_completed']: cols[i].button(f"✅ {i+1}", key=f"d_{i}", disabled=True)
                elif i == ex['sets_completed']: 
                    if cols[i].button(f"Go {i+1}", key=f"g_{i}"):
                        st.session_state.active_workout["exercises"][step]["sets_completed"] += 1
                        save_current_user(st.session_state.current_user)
                        st.rerun()
            with st.form(f"f_{step}"):
                w = st.text_input("Weight", value=ex['my_weight'])
                n = st.text_input("Notes", value=ex['my_notes'])
                if st.form_submit_button("Next"):
                    st.session_state.active_workout["exercises"][step]["my_weight"] = w
                    st.session_state.active_workout["exercises"][step]["my_notes"] = n
                    st.session_state.active_workout["current_step"] += 1
                    save_current_user(st.session_state.current_user)
                    st.rerun()
            if st.button("Abort"):
                st.session_state.active_workout = None
                save_current_user(st.session_state.current_user)
                st.rerun()

# =========================================================
#  ZONE 7: HISTORY
# =========================================================
elif menu == "📜 History":
    st.title("📜 Chronicle")
    for entry in reversed(st.session_state.completed_history):
        st.text(entry)

# =========================================================
#  ZONE 8: ADMIN PANEL (UPDATED)
# =========================================================
elif menu == "👑 Admin Panel" and is_admin:
    st.title("👑 Monarch's Decree")
    
    target_user = st.selectbox("Select Target User", user_list)
    target_data = all_data.get(target_user, init_user_data(target_user))
    
    tab1, tab2, tab3 = st.tabs(["📝 Assign Task", "💰 Manage Market", "✏️ Edit Habits"])
    
    with tab1:
        with st.form("assign_task"):
            t_name = st.text_input("Task Name (e.g. Mow Lawn)")
            t_stat = st.selectbox("Stat Reward", list(target_data["xp"].keys()))
            t_due = st.date_input("Due Date", value=datetime.date.today())
            if st.form_submit_button("Assign Task"):
                target_data["one_time_tasks"].append({
                    "name": t_name, 
                    "stat": t_stat, 
                    "done": False,
                    "due_date": str(t_due)
                })
                admin_save_target_user(target_user, target_data)
                st.success(f"Assigned '{t_name}' to {target_user} due {t_due}!")
    
    with tab2:
        st.write(f"Editing Market for: **{target_user}**")
        # List Existing Market Items
        if target_data["shop"]:
            items_to_del = []
            for item_name, item_price in target_data["shop"].items():
                c1, c2 = st.columns([3, 1])
                c1.info(f"{item_name} ({item_price} GP)")
                if c2.button("🗑️", key=f"del_shop_{item_name}"):
                    items_to_del.append(item_name)
            
            if items_to_del:
                for it in items_to_del:
                    del target_data["shop"][it]
                admin_save_target_user(target_user, target_data)
                st.rerun()
        else:
            st.warning("Market is empty.")
            
        st.divider()
        st.write("Add New Stock")
        with st.form("add_shop"):
            s_name = st.text_input("Reward Name (e.g. Concert Ticket)")
            s_price = st.number_input("Gold Cost", min_value=10, step=10)
            if st.form_submit_button("Stock Market"):
                target_data["shop"][s_name] = s_price
                admin_save_target_user(target_user, target_data)
                st.success(f"Added '{s_name}' to {target_user}'s Market!")
                st.rerun()
                
    with tab3:
        st.write(f"Editing Habits for: **{target_user}**")
        # List Current Habits
        habits_to_delete = []
        for h, v in target_data["habits"].items():
            c1, c2 = st.columns([3, 1])
            c1.info(f"{h} (+15 {v[0]})")
            if c2.button("🗑️", key=f"del_{h}"):
                habits_to_delete.append(h)
        
        if habits_to_delete:
            for h in habits_to_delete:
                del target_data["habits"][h]
            admin_save_target_user(target_user, target_data)
            st.rerun()
            
        st.divider()
        with st.form("new_habit"):
            h_name = st.text_input("New Habit Name (e.g. Walk Dog)")
            h_stat = st.selectbox("Attribute", ["Strength", "Agility", "Vitality", "Intellect", "Spirit", "Sense"])
            if st.form_submit_button("Create Habit"):
                target_data["habits"][h_name] = [h_stat, None]
                admin_save_target_user(target_user, target_data)
                st.success(f"Created habit: {h_name}")
                st.rerun()
