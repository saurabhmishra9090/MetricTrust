from flask import Flask, render_template, jsonify, request
from pathlib import Path
import duckdb
import pandas as pd
from src.metric_logic import find_mt001_violations

app = Flask(__name__)

DB_FILE = Path(__file__).resolve().parent / "data" / "metrictrust.duckdb"

def init_investigation_cases():
    con = duckdb.connect(str(DB_FILE))
    try:
        con.execute("CREATE SEQUENCE IF NOT EXISTS investigation_case_seq START 1")
        con.execute("CREATE SEQUENCE IF NOT EXISTS investigation_case_history_seq START 1")
        con.execute("""
            CREATE TABLE IF NOT EXISTS investigation_cases (
              case_id BIGINT PRIMARY KEY DEFAULT nextval('investigation_case_seq'),
                month VARCHAR NOT NULL,
                status VARCHAR NOT NULL DEFAULT 'Open',
                analyst_notes VARCHAR DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS investigation_case_history (
               history_id BIGINT PRIMARY KEY DEFAULT nextval('investigation_case_history_seq'),
                case_id BIGINT NOT NULL,
                field_name VARCHAR NOT NULL,
                old_value VARCHAR,
                new_value VARCHAR,
                changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)    
    finally:
        con.close()


init_investigation_cases()
def fetch_dashboard_data():
    if not DB_FILE.exists():
        raise FileNotFoundError("MetricTrust database was not found.")
    

    con = duckdb.connect(str(DB_FILE), read_only=True)

    try:
        monthly = con.execute("""
            SELECT
                month,
                total_requests,
                closed_requests,
                missing_closed_dates,
                closure_rate_pct
            FROM monthly_kpi_results
            ORDER BY month
        """).fetchdf()

        return monthly

    finally:
        con.close()


# MetricTrust dedicated workspace routes

@app.route("/trends")
def trends():
    return render_template("trends.html")


@app.route("/investigations")
def investigations():
    return render_template("investigations.html")


@app.route("/definitions")
def definitions():
    if not DB_FILE.exists():
        return "MetricTrust database was not found.", 500

    con = duckdb.connect(str(DB_FILE), read_only=True)

    try:
        definitions_df = con.execute("""
            SELECT
                metric_id,
                metric_name,
                metric_description,
                formula_definition,
                aggregation_grain,
                version,
                effective_from,
                effective_to,
                is_current,
                change_reason
            FROM metric_registry
            ORDER BY metric_id, version
        """).fetchdf()

        definitions = definitions_df.to_dict(orient="records")

        for item in definitions:
            for field in ("effective_from", "effective_to"):
                value = item.get(field)

                if value is None or str(value) in ("NaT", "nan", "None", ""):
                    item[field] = (
                        "Open-ended"
                        if field == "effective_to"
                        else "Not set"
                    )
                else:
                    item[field] = str(value)[:10]

            # Display Boolean values clearly in the template.
            item["is_current"] = bool(item.get("is_current", False))

        return render_template(
            "definitions.html",
            definitions=definitions
        )

    except Exception:
        app.logger.exception("Definition history page failed")
        return "Unable to load metric definitions. Check the Flask terminal.", 500

    finally:
        con.close()


@app.route("/quality")
def quality():
    return render_template("quality.html")


@app.route("/assistant")
def assistant():
    return render_template("assistant.html")


@app.route("/")
def dashboard():
    try:
        monthly = fetch_dashboard_data()

       
        signal_con = duckdb.connect(str(DB_FILE), read_only=True)

        try:
            signal_counts = signal_con.execute("""
                SELECT
                    COALESCE(SUM(CASE
                        WHEN performance_signal THEN 1 ELSE 0
                    END), 0) AS performance_signals,
                    COALESCE(SUM(CASE
                        WHEN data_quality_signal THEN 1 ELSE 0
                    END), 0) AS data_quality_signals
                FROM drift_results
            """).fetchone()

            definition_changes = signal_con.execute("""
                SELECT COUNT(*)
                FROM (
                    SELECT metric_id
                    FROM metric_registry
                    GROUP BY metric_id
                    HAVING COUNT(*) > 1
                ) AS versioned_metrics
            """).fetchone()[0]

        finally:
            signal_con.close()

        summary = {
            "total_requests": int(monthly["total_requests"].sum()),
            "closed_requests": int(monthly["closed_requests"].sum()),
            "performance_signals": int(signal_counts[0] or 0),
            "data_quality_signals": int(signal_counts[1] or 0),
            "definition_changes": int(definition_changes or 0),
        }


        if summary["total_requests"] > 0:
            summary["closure_rate"] = round(
                summary["closed_requests"]
                / summary["total_requests"] * 100,
                2
            )
        else:
            summary["closure_rate"] = 0

        return render_template(
            "index.html",
            summary=summary
        )

    except Exception as exc:
        app.logger.exception("Dashboard data loading failed")
        return f"Dashboard data error: {exc}", 500


@app.route("/api/monthly-kpis")
def monthly_kpis():
    try:
        monthly = fetch_dashboard_data()
        return jsonify(monthly.to_dict(orient="records"))

    except Exception:
        app.logger.exception("Monthly KPI API failed")
        return jsonify({"error": "Unable to load monthly KPI data"}), 500
    
@app.route("/api/reconciliation")
def reconciliation_api():
    raw_file = (
        Path(__file__).resolve().parent
        / "data"
        / "raw"
        / "nyc_311_monthly_sample.csv"
    )

    if not raw_file.exists():
        return jsonify({
            "error": "Raw sample data file was not found."
        }), 404

    try:
        df = pd.read_csv(raw_file)

        violations = find_mt001_violations(df)

        evidence_columns = [
            column
            for column in [
                "unique_key",
                "created_date",
                "agency",
                "status",
                "closed_date",
            ]
            if column in violations.columns
        ]

        records = violations[evidence_columns].copy()
        records = records.astype(object).where(
            pd.notna(records), None
        )

        return jsonify({
            "rule_id": "MT-001",
            "rule_description": (
                "Records marked closed with a missing or invalid "
                "closed date."
            ),
            "source": "nyc_311_monthly_sample.csv",
            "sample_records_checked": int(len(df)),
            "violation_count": int(len(violations)),
            "violations": records.to_dict(orient="records"),
        })

    except Exception:
        app.logger.exception("Reconciliation API failed")
        return jsonify({
            "error": "Unable to calculate reconciliation results."
        }), 500
    
@app.route("/api/investigation-cases", methods=["GET", "POST"])
def investigation_cases_api():
    if request.method == "GET":
        con = None
        try:
            con = duckdb.connect(str(DB_FILE), read_only=True)
            cases = con.execute("""
                SELECT case_id, month, status, analyst_notes,
                       created_at, updated_at
                FROM investigation_cases
                ORDER BY created_at DESC
            """).fetchdf()
            return jsonify(cases.to_dict(orient="records"))
        except Exception:
            app.logger.exception("Investigation cases GET failed")
            return jsonify({
                "error": "Unable to load investigation cases."
            }), 500
        finally:
            if con is not None:
                con.close()

    # POST: create a new investigation case.
    payload = request.get_json(silent=True) or {}
    month = str(payload.get("month", "")).strip()
    if not month:
        return jsonify({"error": "Month is required."}), 400

    notes = str(payload.get("analyst_notes", "")).strip()
    con = None
    try:
        con = duckdb.connect(str(DB_FILE))
        result = con.execute("""
               INSERT INTO investigation_cases (
        case_id, month, analyst_notes
    )
    VALUES (nextval('investigation_case_seq'), ?, ?)
    RETURNING case_id, month, status, analyst_notes,
              created_at, updated_at
""", [month, notes]).fetchone()
        return jsonify({
            "case_id": result[0],
            "month": result[1],
            "status": result[2],
            "analyst_notes": result[3],
            "created_at": str(result[4]),
            "updated_at": str(result[5])
        }), 201

    except Exception:
        app.logger.exception("Investigation cases POST failed")
        return jsonify({
            "error": "Unable to process investigation case."
        }), 500
    finally:
        if con is not None:
            con.close()


@app.route("/api/investigation-cases/<int:case_id>", methods=["PATCH"])

def update_investigation_case(case_id):
    payload = request.get_json(silent=True) or {}

    allowed_fields = {"status", "analyst_notes"}
    if not payload or not set(payload).issubset(allowed_fields):
        return jsonify({
            "error": "Provide status and/or analyst_notes."
        }), 400

    status = payload.get("status")
    notes = payload.get("analyst_notes")

    if status is not None and status not in {
        "Open", "In Progress", "Resolved"
    }:
        return jsonify({
            "error": "Status must be Open, In Progress, or Resolved."
        }), 400

    if notes is not None and not isinstance(notes, str):
        return jsonify({
            "error": "analyst_notes must be text."
        }), 400

    con = duckdb.connect(str(DB_FILE))

    try:
        existing = con.execute(
            """
           SELECT case_id, status, analyst_notes
            FROM investigation_cases
            WHERE case_id = ?
            """,
            [case_id]
        ).fetchone()

        if existing is None:
            return jsonify({
                "error": "Investigation case not found."
            }), 404
        
        if status is not None and status != existing[1]:
            con.execute(
                """
                INSERT INTO investigation_case_history
                   (history_id, case_id, field_name, old_value, new_value)
                VALUES (nextval('investigation_case_history_seq'), ?, ?, ?, ?)
                """,
                [case_id, "status", existing[1], status]
            )

        if notes is not None and notes != existing[2]:
            con.execute(
                """
                INSERT INTO investigation_case_history
                   (history_id, case_id, field_name, old_value, new_value)
               VALUES (nextval('investigation_case_history_seq'), ?, ?, ?, ?)
                """,
                [case_id, "analyst_notes", existing[2], notes]
            )


        if status is not None and notes is not None:
            con.execute(
                """
                UPDATE investigation_cases
                SET status = ?, analyst_notes = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE case_id = ?
                """,
                [status, notes, case_id]
            )

        elif status is not None:
            con.execute(
                """
                UPDATE investigation_cases
                SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE case_id = ?
                """,
                [status, case_id]
            )

        elif notes is not None:
            con.execute(
                """
                UPDATE investigation_cases
                SET analyst_notes = ?, updated_at = CURRENT_TIMESTAMP
                WHERE case_id = ?
                """,
                [notes, case_id]
            )

        updated = con.execute(
            """
            SELECT case_id, month, status, analyst_notes,
                   created_at, updated_at
            FROM investigation_cases
            WHERE case_id = ?
            """,
            [case_id]
        ).fetchone()

        return jsonify({
            "case_id": updated[0],
            "month": updated[1],
            "status": updated[2],
            "analyst_notes": updated[3],
            "created_at": str(updated[4]),
            "updated_at": str(updated[5])
        })

    except Exception:
        app.logger.exception("Investigation case update failed")
        return jsonify({
            "error": "Unable to update investigation case."
        }), 500

    finally:
        con.close()

@app.route("/api/investigation-cases/<int:case_id>/history", methods=["GET"])
def investigation_case_history(case_id):
    con = None

    try:
        con = duckdb.connect(str(DB_FILE), read_only=True)

        history = con.execute(
            """
            SELECT
                history_id,
                case_id,
                field_name,
                old_value,
                new_value,
                changed_at
            FROM investigation_case_history
            WHERE case_id = ?
            ORDER BY changed_at DESC, history_id DESC
            """,
            [case_id]
        ).fetchdf()

        return jsonify(history.to_dict(orient="records"))

    except Exception:
        app.logger.exception("Investigation case history failed")
        return jsonify({
            "error": "Unable to load investigation case history."
        }), 500

    finally:
        if con is not None:
            con.close()

@app.route("/api/assistant", methods=["POST"])
def assistant_api():
    try:
        payload = request.get_json(silent=True) or {}
        question = str(payload.get("question", "")).strip().lower()

        if not question:
            return jsonify({"error": "Please enter a question."}), 400

        monthly = fetch_dashboard_data()

        if monthly is None or monthly.empty:
            return jsonify({
                "error": "No monthly KPI data is available."
            }), 503

        total_requests = int(monthly["total_requests"].sum())
        closed_requests = int(monthly["closed_requests"].sum())
        missing_dates = int(monthly["missing_closed_dates"].sum())

        closure_rate = (
            round(closed_requests / total_requests * 100, 2)
            if total_requests else 0
        )

        # Prepare numeric monthly KPI data
        analysis = monthly.copy()

        for column in [
            "total_requests",
            "closed_requests",
            "missing_closed_dates"
        ]:
            analysis[column] = pd.to_numeric(
                analysis[column], errors="coerce"
            ).fillna(0)

        analysis["closure_rate_pct"] = (
            analysis["closed_requests"]
            .div(analysis["total_requests"].replace(0, float("nan")))
            .mul(100)
        )

        analysis = analysis.sort_values("month").reset_index(drop=True)
        valid_rates = analysis.dropna(subset=["closure_rate_pct"])

        # Highest and lowest closure-rate months
        highest_month = None
        lowest_month = None

        if not valid_rates.empty:
            highest_month = valid_rates.loc[
                valid_rates["closure_rate_pct"].idxmax()
            ]
            lowest_month = valid_rates.loc[
                valid_rates["closure_rate_pct"].idxmin()
            ]

        asks_lowest = any(word in question for word in [
            "lowest", "minimum", "min closure", "worst month"
        ])

        asks_highest = any(word in question for word in [
            "highest", "maximum", "max closure", "best month"
        ])

        asks_monthly_change = any(phrase in question for phrase in [
            "month-over-month",
            "month over month",
            "compared with last month",
            "compared to last month",
            "monthly change",
            "closure rate change"
        ])

        asks_missing_months = any(phrase in question for phrase in [
            "which months",
            "list months",
            "months have missing",
            "missing closure dates"
        ])

        # Highest / lowest closure rate
        if asks_highest or asks_lowest:
            selected_month = (
                lowest_month if asks_lowest else highest_month
            )

            if selected_month is None:
                answer = (
                    "Closure rates cannot be calculated because "
                    "no month has a positive request total."
                )
            else:
                label = "lowest" if asks_lowest else "highest"
                answer = (
                    f"The {label} closure rate was in "
                    f"{selected_month['month']}: "
                    f"{selected_month['closure_rate_pct']:.2f}% "
                    f"({int(selected_month['closed_requests']):,} closed out of "
                    f"{int(selected_month['total_requests']):,} requests)."
                )

        # Month-over-month change
        elif asks_monthly_change:
            if len(valid_rates) < 2:
                answer = (
                    "At least two months with valid closure rates "
                    "are required for a month-over-month comparison."
                )
            else:
                previous = valid_rates.iloc[-2]
                current = valid_rates.iloc[-1]
                change = (
                    current["closure_rate_pct"]
                    - previous["closure_rate_pct"]
                )

                if change > 0:
                    direction = "increased"
                elif change < 0:
                    direction = "decreased"
                else:
                    direction = "did not change"

                answer = (
                    f"From {previous['month']} to {current['month']}, "
                    f"the closure rate {direction} by {abs(change):.2f} "
                    f"percentage points, from "
                    f"{previous['closure_rate_pct']:.2f}% to "
                    f"{current['closure_rate_pct']:.2f}%. "
                    "This compares the last two months with valid rates."
                )

        # List specific months with missing closure dates
        elif asks_missing_months:
            missing_months = analysis[
                analysis["missing_closed_dates"] > 0
            ]

            if missing_months.empty:
                answer = (
                    "No months in the available monthly data "
                    "report missing closure dates."
                )
            else:
                details = "; ".join(
                    f"{row['month']}: "
                    f"{int(row['missing_closed_dates']):,}"
                    for _, row in missing_months.iterrows()
                )

                answer = (
                    f"{len(missing_months)} month(s) report missing "
                    f"closure dates: {details}. These are monthly "
                    "aggregate signals. Verify transaction-level evidence "
                    "before concluding that a data-quality violation occurred."
                )

        # Overall closure rate
        elif "closure" in question and (
            "rate" in question or "overall" in question
        ):
            answer = (
                f"The aggregate closure rate across the available "
                f"monthly sample is {closure_rate}%. There are "
                f"{total_requests:,} requests and {closed_requests:,} "
                "closed requests in the monthly aggregates. "
                "These are sample-based figures, not citywide totals."
            )

        # Overall missing closure dates
        elif "missing" in question and (
            "date" in question or "closure" in question
        ):
            answer = (
                f"The monthly aggregates report {missing_dates:,} "
                f"missing closure dates across {len(monthly)} months. "
                "This is a sum of monthly counts, not proof of a "
                "transaction-level data-quality violation."
            )

        # KPI investigation guidance
        elif (
            "investigat" in question
            or "kpi change" in question
            or "definition" in question
        ):
            answer = (
                "To investigate a KPI change: "
                "1) compare the affected months, "
                "2) check data-quality signals and missing dates, "
                "3) review metric definition history, and "
                "4) reconcile against transaction-level records. "
                "A signal does not establish the root cause."
            )

        else:
            answer = (
                "I can answer questions about overall closure rate, "
                "highest and lowest closure-rate months, "
                "month-over-month changes, missing closure dates, "
                "and KPI investigation guidance. Try one of those topics."
            )

        return jsonify({"answer": answer})

    except Exception:
        app.logger.exception("MetricTrust assistant API failed")
        return jsonify({
            "error": "Unable to analyze KPI data. Check the Flask terminal."
        }), 500


if __name__ == "__main__":
    app.run(debug=True)





if __name__ == "__main__":
    app.run(debug=True)
