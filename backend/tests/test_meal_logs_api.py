from fastapi.testclient import TestClient

from backend.app.main import app


client = TestClient(app)


def test_confirm_planned_meal_saves_meal_log_from_current_plan():
    response = client.post(
        "/api/meal-logs/confirm-planned-meal",
        json={
            "user_id": "demo-user-945",
            "plan_id": "plan-2026-07-11-demo",
            "date": "2026-07-11",
            "meal_id": "meal-breakfast-1"
        }
    )

    assert response.status_code == 200
    body = response.json()
    assert body["error"] is None
    assert body["data"]["meal_log_id"].startswith("meal-log-meal-breakfast-1-")
    assert body["data"]["source"] == "planned_meal_confirmation"
    assert body["data"]["meal_name"] == "早餐"
    assert body["data"]["calories"] == 387
    assert body["data"]["protein_g"] == 30
    assert body["data"]["carbs_g"] == 53
    assert body["data"]["fat_g"] == 7
    assert body["data"]["foods"][0]["name"] == "希腊酸奶"


def test_save_manual_meal_sums_food_macros():
    response = client.post(
        "/api/meal-logs",
        json={
            "user_id": "demo-user-945",
            "date": "2026-07-11",
            "meal_name": "午餐",
            "foods": [
                {
                    "name": "鸡胸肉饭碗",
                    "portion": "1 bowl",
                    "calories": 620,
                    "protein_g": 42,
                    "carbs_g": 78,
                    "fat_g": 16
                },
                {
                    "name": "鸡蛋",
                    "portion": "1 个",
                    "calories": 70,
                    "protein_g": 6,
                    "carbs_g": 1,
                    "fat_g": 5
                }
            ],
            "notes": "外食估算。"
        }
    )

    assert response.status_code == 200
    body = response.json()
    assert body["error"] is None
    assert body["data"]["meal_log_id"].startswith("meal-log-manual-2026-07-11-")
    assert body["data"]["source"] == "manual_entry"
    assert body["data"]["calories"] == 690
    assert body["data"]["protein_g"] == 48
    assert body["data"]["carbs_g"] == 79
    assert body["data"]["fat_g"] == 21


def test_list_meal_logs_returns_saved_logs_for_user():
    client.post(
        "/api/meal-logs",
        json={
            "user_id": "demo-user-945",
            "date": "2026-07-11",
            "meal_name": "加餐",
            "foods": [
                {
                    "name": "香蕉",
                    "portion": "1 根",
                    "calories": 100,
                    "protein_g": 1,
                    "carbs_g": 27,
                    "fat_g": 0
                }
            ]
        }
    )

    response = client.get("/api/meal-logs", params={"user_id": "demo-user-945"})

    assert response.status_code == 200
    body = response.json()
    assert body["error"] is None
    assert any(log["meal_name"] == "加餐" for log in body["data"])


def test_confirm_planned_meal_rejects_missing_meal():
    response = client.post(
        "/api/meal-logs/confirm-planned-meal",
        json={
            "user_id": "demo-user-945",
            "plan_id": "plan-2026-07-11-demo",
            "date": "2026-07-11",
            "meal_id": "missing-meal"
        }
    )

    assert response.status_code == 404
    assert response.json() == {
        "data": None,
        "error": {
            "code": "NOT_FOUND",
            "message": "Planned meal not found.",
            "details": {
                "user_id": "demo-user-945",
                "plan_id": "plan-2026-07-11-demo",
                "date": "2026-07-11",
                "meal_id": "missing-meal"
            }
        }
    }


def test_save_manual_meal_rejects_unknown_user():
    response = client.post(
        "/api/meal-logs",
        json={
            "user_id": "missing-user",
            "date": "2026-07-11",
            "meal_name": "午餐",
            "foods": [
                {
                    "name": "米饭",
                    "portion": "1 bowl",
                    "calories": 240,
                    "protein_g": 4,
                    "carbs_g": 52,
                    "fat_g": 1
                }
            ]
        }
    )

    assert response.status_code == 404
    assert response.json() == {
        "data": None,
        "error": {
            "code": "NOT_FOUND",
            "message": "Demo user not found.",
            "details": {"user_id": "missing-user"}
        }
    }
