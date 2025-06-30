from flask import Flask, request, render_template, send_file
import pandas as pd
import random
from itertools import permutations
from collections import defaultdict
from fpdf import FPDF
import tempfile
import os

app = Flask(__name__)

def generate_schedule(players, scores, rounds=10):
    played_with = defaultdict(set)
    played_against = defaultdict(lambda: defaultdict(int))
    schedule = []

    attempts = 0
    max_attempts = 20000  # increased from 5000 to allow more scheduling attempts

    while len(schedule) < rounds and attempts < max_attempts:
        attempts += 1
        random.shuffle(players)
        round_matches = []
        used = set()
        valid = True

        for i in range(0, len(players), 4):
            group = players[i:i + 4]
            best_match = None
            best_score = float('inf')

            for perm in permutations(group):
                team1, team2 = (perm[0], perm[1]), (perm[2], perm[3])
                if (team1[0] not in used and team1[1] not in used and
                    team2[0] not in used and team2[1] not in used and
                    team1[1] not in played_with[team1[0]] and
                    team2[1] not in played_with[team2[0]] and
                    all(played_against[p1][p2] < 3 for p1 in team1 for p2 in team2)):

                    score = abs((scores[team1[0]] + scores[team1[1]]) / 2 -
                                (scores[team2[0]] + scores[team2[1]]) / 2)
                    if score < best_score:
                        best_score = score
                        best_match = (team1, team2)

            if best_match:
                round_matches.append(best_match)
                used.update(best_match[0] + best_match[1])
            else:
                valid = False
                break

        if valid and len(round_matches) == len(players) // 4:
            for team1, team2 in round_matches:
                played_with[team1[0]].add(team1[1])
                played_with[team1[1]].add(team1[0])
                played_with[team2[0]].add(team2[1])
                played_with[team2[1]].add(team2[0])
                for p1 in team1:
                    for p2 in team2:
                        played_against[p1][p2] += 1
                        played_against[p2][p1] += 1
            schedule.append(round_matches)

    return schedule

def create_pdf(schedule, player_numbers):
    reverse_map = {v: k for k, v in player_numbers.items()}
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=10)
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, "GOAT, Inc.", ln=True, align="C")
    pdf.set_font("Arial", '', 12)
    pdf.cell(200, 10, "Goat League - Auto Schedule", ln=True, align="C")
    pdf.ln(10)

    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, "Player Number Mapping:", ln=True)
    pdf.set_font("Arial", '', 10)
    for number, name in sorted(reverse_map.items()):
        pdf.cell(100, 8, f"{number}: {name}", ln=True)

    pdf.ln(5)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, "Match Schedule:", ln=True)
    pdf.set_font("Arial", '', 10)

    for rnd_index, matches in enumerate(schedule, 1):
        pdf.cell(200, 8, f"Round {rnd_index}", ln=True)
        for team1, team2 in matches:
            t1a, t1b = player_numbers[team1[0]], player_numbers[team1[1]]
            t2a, t2b = player_numbers[team2[0]], player_numbers[team2[1]]
            pdf.cell(200, 8, f"  {t1a}-{t1b} vs {t2a}-{t2b}", ln=True)
        pdf.ln(2)

    pdf.output(tmp.name)
    return tmp.name

@app.route('/', methods=['GET', 'POST'])
def index():
shuffle_numbers = False  # prevent UnboundLocalError on GET
    if request.method == 'POST':
        num_players = int(request.form['numPlayers'])
        use_weighted = request.form['useWeights'] == 'yes'
        file = request.files['playerList']
        df = pd.read_excel(file)

        df = df.sort_values(by="Weighted Score", ascending=False).head(num_players).reset_index(drop=True)
        players = df['Player'].tolist()
        scores = {name: float(df.loc[df['Player'] == name, 'Weighted Score']) if use_weighted else 0 for name in players}
        if shuffle_numbers and players:
            random.shuffle(players)
        player_numbers = {name: i+1 for i, name in enumerate(players)}

        rounds = int(request.form.get('rounds', 10))
        shuffle_numbers = request.form.get('shuffleNumbers', 'no') == 'yes'
        schedule = generate_schedule(players, scores, rounds)
        pdf_path = create_pdf(schedule, player_numbers)
        return send_file(pdf_path, as_attachment=True)

    return render_template('index.html')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)