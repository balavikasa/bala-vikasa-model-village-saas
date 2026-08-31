from __future__ import annotations

from flask import (
    Blueprint,
    current_app,
    make_response,
    redirect,
    render_template,
    send_from_directory,
    url_for,
)
from flask_login import current_user, login_required

from .models import Role
from .scoping import role_required
from .services.profiles import da_profile, pc_profile, pm_profile, village_profile

bp = Blueprint("pages", __name__)


@bp.get("/")
@login_required
def home():
    if current_user.role == Role.DA:
        return redirect(url_for("planning.action_plans_page"))
    return redirect(url_for("pages.overview"))


@bp.get("/overview")
@login_required
def overview():
    if current_user.role == Role.DA:
        return redirect(url_for("planning.action_plans_page"))
    return render_template("overview.html")


@bp.get("/field/attendance")
@login_required
@role_required(Role.DA)
def attendance():
    return render_template("field.html", entry_type="attendance")


@bp.get("/field/specials")
@login_required
@role_required(Role.DA)
def specials():
    return render_template("field.html", entry_type="specials")


@bp.get("/directory")
@login_required
def directory():
    return render_template("directory.html")




@bp.get("/map")
@login_required
def map_page():
    return render_template("map.html")


@bp.get("/directory/da/<int:da_id>")
@login_required
def da_profile_page(da_id: int):
    profile = da_profile(current_user._get_current_object(), da_id)
    if profile is None:
        return render_template("403.html"), 404
    return render_template("profile.html", profile=profile)


@bp.get("/directory/village/<int:village_id>")
@login_required
def village_profile_page(village_id: int):
    profile = village_profile(current_user._get_current_object(), village_id)
    if profile is None:
        return render_template("403.html"), 404
    return render_template("profile.html", profile=profile)


@bp.get("/directory/pc/<int:pc_id>")
@login_required
def pc_profile_page(pc_id: int):
    profile = pc_profile(current_user._get_current_object(), pc_id)
    if profile is None:
        return render_template("403.html"), 404
    return render_template("profile.html", profile=profile)


@bp.get("/directory/pm/<int:pm_id>")
@login_required
def pm_profile_page(pm_id: int):
    profile = pm_profile(current_user._get_current_object(), pm_id)
    if profile is None:
        return render_template("403.html"), 404
    return render_template("profile.html", profile=profile)


@bp.get("/monitoring")
@login_required
@role_required(Role.ADMIN, Role.PM, Role.PC)
def monitoring():
    return render_template("monitoring.html")



@bp.get("/analytics")
@login_required
@role_required(Role.ADMIN, Role.PM, Role.PC)
def analytics():
    return render_template("analytics.html")


@bp.get("/admin")
@login_required
@role_required(Role.ADMIN)
def admin():
    return render_template("admin.html")


@bp.get("/offline")
def offline():
    return render_template("offline.html")


@bp.get("/sw.js")
def service_worker():
    response = make_response(send_from_directory(current_app.static_folder, "sw.js"))
    response.headers["Content-Type"] = "application/javascript; charset=utf-8"
    response.headers["Service-Worker-Allowed"] = "/"
    response.headers["Cache-Control"] = "no-cache"
    return response


@bp.get("/manifest.json")
def manifest():
    response = make_response(send_from_directory(current_app.static_folder, "manifest.json"))
    response.headers["Content-Type"] = "application/manifest+json"
    return response
