from enum import StrEnum

from baja.models import Role


class Permission(StrEnum):
    company_manage = "company:manage"
    users_read = "users:read"
    users_manage = "users:manage"
    properties_read = "properties:read"
    properties_read_all = "properties:read_all"
    properties_manage = "properties:manage"
    transactions_read = "transactions:read"
    transactions_manage = "transactions:manage"
    guest_expenses_read = "guest_expenses:read"
    guest_expenses_manage = "guest_expenses:manage"
    recurring_charges_manage = "recurring_charges:manage"


ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.owner: frozenset(Permission),
    Role.manager: frozenset(
        {
            Permission.users_read,
            Permission.properties_read,
            Permission.properties_read_all,
            Permission.properties_manage,
            Permission.transactions_read,
            Permission.transactions_manage,
            Permission.guest_expenses_read,
            Permission.guest_expenses_manage,
            Permission.recurring_charges_manage,
        }
    ),
    Role.homeowner: frozenset(
        {
            Permission.properties_read,
            Permission.transactions_read,
            Permission.guest_expenses_read,
        }
    ),
}

DENIED: dict[Permission, str] = {
    Permission.company_manage: "Only an owner can change the company settings.",
    Permission.users_read: "Only owners and managers can see the users.",
    Permission.users_manage: "Only an owner can manage users.",
    Permission.properties_read: "You can't view properties.",
    Permission.properties_read_all: "You can only view the properties assigned to you.",
    Permission.properties_manage: "Only owners and managers can manage properties.",
    Permission.transactions_read: "You can't view transactions.",
    Permission.transactions_manage: "Only owners and managers can record transactions.",
    Permission.guest_expenses_read: "You can't view guest expenses.",
    Permission.guest_expenses_manage: (
        "Only owners and managers can record guest expenses."
    ),
    Permission.recurring_charges_manage: (
        "Only owners and managers can manage recurring charges."
    ),
}


def has_permission(role: Role, permission: Permission) -> bool:
    return permission in ROLE_PERMISSIONS[role]
