from sqladmin import Admin, ModelView
from ..core.models import User, Plan, Server, Subscription, Transaction

class UserAdmin(ModelView, model=User):
    column_list = [User.telegram_id, User.username, User.balance, User.is_banned]
    column_searchable_list = [User.username, User.telegram_id]

class PlanAdmin(ModelView, model=Plan):
    column_list = [Plan.id, Plan.name, Plan.price, Plan.duration_days, Plan.is_active]

class ServerAdmin(ModelView, model=Server):
    column_list = [Server.id, Server.host_url, Server.username]

class SubscriptionAdmin(ModelView, model=Subscription):
    # Убедись, что plan_id здесь есть
    column_list = [Subscription.id, Subscription.user_id, Subscription.plan_id, Subscription.expire_date, Subscription.status]

class TransactionAdmin(ModelView, model=Transaction):
    column_list = [Transaction.id, Transaction.user_id, Transaction.amount, Transaction.status, Transaction.created_at]

# --- ВОТ ЭТА ФУНКЦИЯ ПРОПАЛА ---
def setup_admin(app, engine):
    admin = Admin(app, engine)
    admin.add_view(UserAdmin)
    admin.add_view(PlanAdmin)
    admin.add_view(ServerAdmin)
    admin.add_view(SubscriptionAdmin)
    admin.add_view(TransactionAdmin)
    return admin
