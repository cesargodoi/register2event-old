from datetime import date


#  new  #######################################################################
@auth.requires_login()
@auth.requires(
    auth.has_membership("root")
    or auth.has_membership("admin")
    or auth.has_membership("office")
)
def new():
    new = _guest_form()

    if new.process().accepted:
        guesid = int(new.process().vars.id)

        if request.vars.reg:
            redirect(URL("register", "confirm_guest", vars={"guesid": guesid}))

        redirect(URL("show", vars={"guesid": guesid, "tab": "home"}))

    return dict(form=new)


#  edit  ######################################################################
@auth.requires_login()
@auth.requires(
    auth.has_membership("root")
    or auth.has_membership("admin")
    or auth.has_membership("office")
)
def edit():
    guesid = request.vars.guesid

    edit = _guest_form(instance=guesid)

    if edit.process().accepted:
        if request.vars.on_reg:
            redirect(URL("register", "confirm_guest", vars={"guesid": guesid}))
        redirect(URL("show", vars={"guesid": guesid, "tab": "home"}))

    return dict(form=edit, guest=guesid)


#  new_guest_stay  ############################################################
@auth.requires_login()
@auth.requires(
    auth.has_membership("root")
    or auth.has_membership("admin")
    or auth.has_membership("office")
)
def new_stay():
    new_stay = _stay_form()
    if new_stay.process().accepted:
        if request.vars.on_reg:
            redirect(
                URL(
                    "register",
                    "confirm_guest",
                    vars={"guesid": request.vars.guest_id},
                )
            )
        else:
            redirect(
                URL(
                    "show",
                    vars={
                        "guesid": new_stay.process().vars.guesid,
                        "tab": "stay",
                    },
                )
            )

    return dict(form=new_stay, guesid=request.vars.guesid)


#  edit stay  #################################################################
@auth.requires_login()
@auth.requires(
    auth.has_membership("root")
    or auth.has_membership("admin")
    or auth.has_membership("office")
)
def edit_stay():
    guest = Guest[request.vars.guest_id]

    edit_stay = _stay_form(instance=request.vars.stayid)

    if edit_stay.process().accepted:
        if request.vars.on_reg:
            redirect(
                URL(
                    "register",
                    "confirm_guest",
                    vars={"guesid": request.vars.guest_id},
                )
            )
        else:
            redirect(
                URL(
                    "show",
                    vars={"guesid": request.vars.guest_id, "tab": "stay"},
                )
            )
    return dict(form=edit_stay, guest=guest.name, stay=request.vars.stayid)


#  list  ######################################################################
@auth.requires_login()
def list():
    # get page
    page = int(request.vars.page) if request.vars.page else 1

    # if exists session.mapp or session.register delete it
    if session.mapp or session.register:
        clear_session()

    # search
    search = FORM(
        INPUT(_name="term", _class="form-control me-1"),
        INPUT(
            _type="submit",
            _class="btn btn-outline-success me-2",
            _value=T("search"),
        ),
        _class="d-flex",
    )
    search.element(_name="term")["_style"] = "width: 15rem;"
    search.element(_name="term")["_placeholder"] = T("search")

    # term
    term = request.vars.term or ""

    # select query
    if not term:
        query = (
            (Guest.id > 0)
            & (Guest.is_active == True)
            & (Guest.center == auth.user.center)
        )
    else:
        if term.isdigit():
            query = (Guest.enrollment == term) & (
                Guest.center == auth.user.center
            )
        else:
            like_term = des(f"%%{term.lower()}%%")
            query = (
                (Guest.name_sa.lower().like(like_term))
                & (Guest.is_active == True)
                & (Guest.center == auth.user.center)
            )

    # get rows
    rows = db(query).select(orderby=Guest.name_sa, limitby=(0, 10))

    return dict(search=search.process(), rows=rows, page=page, term=term)


def infinite_scroll():
    response.view = "guest/guests.html"
    # get page
    page = int(request.vars.page)
    regs = 10
    # set vars
    term = request.vars.term or ""
    # select query
    if not term:
        query = (
            (Guest.id > 0)
            & (Guest.is_active == True)
            & (Guest.center == auth.user.center)
        )
    else:
        if term.isdigit():
            query = (Guest.enrollment == term) & (
                Guest.center == auth.user.center
            )
        else:
            like_term = des(f"%%{term.lower()}%%")
            query = (
                (Guest.name_sa.lower().like(like_term))
                & (Guest.is_active == True)
                & (Guest.center == auth.user.center)
            )
    # get limitby
    _limitby = (regs * (page - 1), regs * page)
    # get rows
    rows = db(query).select(orderby=Guest.name_sa, limitby=_limitby)

    return dict(rows=rows, page=page, term=term)


#  show  ######################################################################
@auth.requires_login()
def show():
    guesid = request.vars.guesid
    guest = Guest[guesid] or redirect(URL("list"))
    guest.age = (
        (date.today() - guest.birthday).days // 365 if guest.birthday else 0
    )
    stays = db(Guest_Stay.guesid == guesid).select() or None
    credit_log = guest.credit_log.select(orderby=~Credit_Log.id)
    historic = db(Register.guesid == guesid).select(
        orderby=~Register.created_on
    )
    tab = request.vars.tab if request.vars.tab else "home"

    return dict(
        guest=guest,
        stays=stays,
        credit_log=credit_log,
        historic=historic,
        tab_pres=tab,
    )


#  delete  ####################################################################
@auth.requires_login()
@auth.requires(auth.has_membership("root") or auth.has_membership("admin"))
def delete():
    guesid = int(request.args(0)) or redirect(URL("list"))
    guest = Guest[guesid]
    if db(Register.guesid == guesid).select():
        guest.update_record(is_active=False)
    else:
        guest.delete_record()
    return "..."


#  delete stay  ###############################################################
@auth.requires_login()
@auth.requires(auth.has_membership("root") or auth.has_membership("admin"))
def delete_stay():
    stay = Guest_Stay[request.args(0)]
    stay.delete_record()
    return "..."


#  forms  #####################################################################
def _guest_form(instance=None):
    form = (
        SQLFORM(Guest, instance, submit_button=T("Update"))
        if instance
        else SQLFORM(Guest, submit_button=T("Add"))
    )
    # adjust fields
    form.element("form")["_class"] = ""
    if auth.has_membership("root") or auth.has_membership("admin"):
        form.element("option", _value=int(auth.user.center))[
            "_selected"
        ] = "selected"
    elif auth.user.center:
        form.element(_id="guest_center__row")["_class"] = "d-none"
        form.element("option", _value=int(auth.user.center))[
            "_selected"
        ] = "selected"
    if not auth.has_membership("root"):
        form.element(_id="guest_credit__row")["_class"] = "d-none"
    if instance:
        form.element(_id="guest_id__row")["_class"] = "d-none"
        form.element(_id="guest_name_sa__row")["_class"] = "d-none"
    form.element(_name="ps")["_rows"] = 2
    form.element(_id="submit_record__row")["_class"] = "mt-3 text-end"
    submit_class = "btn btn-outline-{} btn-lg mb-4".format(
        "secondary" if instance else "primary"
    )
    form.element(_type="submit")["_class"] = submit_class

    return form


def _stay_form(instance=None):
    form = (
        SQLFORM(Guest_Stay, instance, submit_button=T("Update"))
        if instance
        else SQLFORM(Guest_Stay, submit_button=T("Add"))
    )
    # adjust fields - common elements (add/update)
    form.element("form")["_class"] = ""
    form.element(_id="guest_stay_guesid__row")["_class"] = "d-none"

    if request.vars.guest_id:
        elm_guesid = form.element(_name="guesid")
        elm_guesid.element("option", _value=request.vars.guest_id)[
            "_selected"
        ] = "selected"

    form.element(_name="ps")["_rows"] = 2
    form.element(_id="submit_record__row")["_class"] = "mt-3 text-end"
    submit_class = "btn btn-outline-{} btn-lg mb-4".format(
        "secondary" if instance else "primary"
    )
    form.element(_type="submit")["_class"] = submit_class

    if instance:
        form.element(_id="guest_stay_id__row")["_class"] = "d-none"
        form.element(_name="description")["_placeholder"] = T(
            "describe the tasks"
        )
        form.element(_name="description")["_rows"] = 2

        if auth.has_membership("office"):
            form.element(_id="guest_stay_bedroom__row")["_class"] = "d-none"
            form.element(_id="guest_stay_bedroom_alt__row")[
                "_class"
            ] = "d-none"
            form.element(_id="guest_stay_description__row")[
                "_class"
            ] = "d-none"

        if auth.has_membership("root") or auth.has_membership("admin"):
            form.element(_name="description")["_rows"] = 2

    else:
        form.element(_id="guest_stay_bedroom__row")["_class"] = "d-none"
        form.element(_id="guest_stay_bedroom_alt__row")["_class"] = "d-none"
        form.element(_id="guest_stay_description__row")["_class"] = "d-none"

    return form
