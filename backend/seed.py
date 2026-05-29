from app.sql_scripts import apply_seed_data


def seed_database():
    """Apply seed data from database/seed.sql."""
    apply_seed_data()
    print("Seed data applied from database/seed.sql")


if __name__ == "__main__":
    seed_database()
