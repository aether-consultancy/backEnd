# NOTE: multi-parent linking (a kid claimed by more than one parent
# account) is not implemented yet. Kid currently has a single
# parent_id FK. This constant exists so the future many-to-many
# KidParentLink table (or similar) has a hard ceiling to enforce
# against from day one, instead of being retrofitted later.
MAX_PARENTS_PER_KID = 2

MIN_AGE = 3
MAX_AGE = 19


def is_valid_age(age: int | None) -> bool:
    if age is None:
        return True
    return MIN_AGE <= age <= MAX_AGE


def is_duplicate_kid_name(existing_names: list[str], full_name: str) -> bool:
    return full_name.strip().lower() in [n.strip().lower() for n in existing_names]


def can_link_another_parent(current_parent_count: int) -> bool:
    return current_parent_count < MAX_PARENTS_PER_KID
