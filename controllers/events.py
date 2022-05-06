# -*- coding: utf-8 -*-
from datetime import date


#  new  #######################################################################
@auth.requires_login()
@auth.requires(auth.has_membership("root") or auth.has_membership("admin"))
def new():
    new = _event_form()

    if new.process().accepted:
        from gluon.custom_import import track_changes
        import Mapp_Utils as Mapp

        track_changes(True)

        evenid = int(new.process().vars.id)
        Mapp.update_mapping(evenid)

        redirect(URL("show", vars={"evenid": evenid}))

    return dict(form=new)


#  edit  ######################################################################
@auth.requires_login()
@auth.requires(auth.has_membership("root") or auth.has_membership("admin"))
def edit():
    evenid = request.vars.evenid

    edit = _event_form(instance=evenid)

    if edit.process().accepted:
        redirect(URL("show", vars={"evenid": evenid}))
    return dict(form=edit, event=evenid)


# list
@auth.requires_login()
def list():
    from gluon import current

    # get page
    page = int(request.vars.page) if request.vars.page else 1

    # if exists session.mapp or session.register delete it
    if session.mapp or session.register:
        clear_session()
    session.referer = []

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
    search.element(_name="term")["_style"] = "width: 220px;"
    search.element(_name="term")["_placeholder"] = T("MM/YYYY")

    # select query
    qry = (Events.id > 0) & (Events.is_active == True)
    if request.vars.term == "":
        qry = (Events.id > 0) & (Events.is_active == True)
        current.request.get_vars.page = 1
    elif request.vars.term:
        if "/" in request.vars.term:
            term = request.vars.term.split("/")
            qry = (Events.start_date.month() == term[0]) & (
                Events.start_date.year() == term[1]
            )
        current.request.get_vars.page = 1
    elif request.vars.t:
        term = request.vars.t.split("/")
        qry = (Events.start_date.month() == term[0]) & (
            Events.start_date.year() == term[1]
        )

    # gen pagination
    paginator = gen_of_pagination(query=qry, page=page, paginate=25)

    # get rows
    rows = db(qry).select(
        orderby=~Events.start_date, limitby=paginator.limitby
    )

    for r in rows:
        r.guests = db(
            (Register.evenid == r.id)
            & (Register.is_active == True)
            & (Register.credit == False)
        ).count()
        r.centid = r.center

    return dict(
        search=search.process(),
        rows=rows,
        page=paginator.page,
        records=paginator.records,
        total_pages=paginator.total_pages,
    )


# show
@auth.requires_login()
def show():
    # get page
    page = int(request.vars.page) if request.vars.page else 1
    clear_session()

    # set vars
    evenid = request.vars.evenid
    admin_view = request.vars.admin_view
    view_credits = True if request.vars.view_credits == "True" else False
    event = Events[evenid] or redirect(URL("list"))
    all_registrations = [
        reg
        for reg in event.register.select()
        if (reg.credit == True if view_credits else reg.credit == False)
        and reg.is_active == True
    ]
    all_regs = sorted(all_registrations, key=lambda x: x.guesid.name_sa)
    total_registers = len(all_regs)

    # get registers by center
    registers = get_registers_by_center(admin_view, view_credits, all_regs)

    ids = [g.guesid for g in registers]
    lates = [g.guesid for g in registers if g.late]

    # search
    search = FORM(
        DIV(
            INPUT(_name="term", _class="form-control me-1"),
            _class="form-group",
        ),
        INPUT(
            _type="submit",
            _class="btn btn-outline-success me-2",
            _value=T("search"),
        ),
        DIV(
            LABEL(
                INPUT(
                    _name="unalloc",
                    _type="checkbox",
                    _class="form-check-input",
                ),
                T("not hosteds"),
                _class="form-check-label",
            ),
            _class="form-check",
            _id="unalloc",
        ),
        _class="d-flex",
    )
    if not admin_view:
        search.element(_id="unalloc")["_style"] = "display:none;"
    search.element(_name="term")["_style"] = "width: 150px;"
    search.element(_name="term")["_placeholder"] = T("search")

    # select query
    extr_vars = {}
    term = request.vars.term or ""

    if not term:
        rows = registers[:10]
    else:
        rows = [
            reg
            for reg in registers
            if term.lower() in reg.guesid.name_sa.lower()
        ][:10]

    for reg in rows:
        reg.guest_name = reg.guesid.name
        if reg.lodge == "LDG" and reg.bedroom:
            reg.bedroom_name = reg.bedroom.bedroom
            reg.bedroom_building = reg.bedroom.builid.building
        elif reg.lodge == "LDG" and not reg.bedroom:
            reg.bedroom = "unalloc"
        else:
            reg.bedroom = None
        reg.age = (
            (date.today() - reg.guesid.birthday).days // 365
            if reg.guesid.birthday
            else 0
        )

    return dict(
        search=search.process(),
        event=event,
        rows=rows,
        event_records=len(ids),
        lates=lates,
        page=page,
        term=term,
        total_registers=total_registers,
        admin_view=admin_view,
        view_credits=view_credits,
    )


# helper
def get_registers_by_center(admin_view, view_credits, all_event_registrations):
    if auth.has_membership("root") or (
        auth.has_membership("admin") and auth.user.center == event.center.id
    ):
        if admin_view:
            session.admin_view = True
            registrations = [
                reg
                for reg in all_event_registrations
                if (
                    reg.credit == True if view_credits else reg.credit == False
                )
            ]
            if request.vars._formkey:
                if request.vars.unalloc:
                    registrations = [
                        reg
                        for reg in registrations
                        if not reg.bedroom
                        and reg.lodge == "LDG"
                        and reg.is_active
                    ]
            else:
                if request.get_vars.unall:
                    registrations = [
                        reg
                        for reg in registrations
                        if not reg.bedroom
                        and reg.lodge == "LDG"
                        and reg.is_active
                    ]
        else:
            if session.admin_view:
                del session["admin_view"]
            registrations = [
                reg
                for reg in all_event_registrations
                if reg.guesid.center == auth.user.center
                and (
                    reg.credit == True if view_credits else reg.credit == False
                )
            ]
    else:
        registrations = [
            reg
            for reg in all_event_registrations
            if reg.guesid.center == auth.user.center
            and (reg.credit == True if view_credits else reg.credit == False)
        ]

    return registrations


def infinite_scroll():
    response.view = "events/registrations.html"
    # get page
    page = int(request.vars.page)
    regs = 10
    # set vars
    evenid = request.vars.evenid
    admin_view = request.vars.admin_view
    view_credits = True if request.vars.view_credits == "True" else False
    event = Events[evenid] or redirect(URL("list"))
    all_registrations = [
        reg
        for reg in event.register.select()
        if (reg.credit == True if view_credits else reg.credit == False)
        and reg.is_active == True
    ]
    all_regs = sorted(all_registrations, key=lambda x: x.guesid.name_sa)
    total_registers = len(all_regs)

    # get registers by center
    registers = get_registers_by_center(admin_view, view_credits, all_regs)

    ids = [g.guesid for g in registers]
    lates = [g.guesid for g in registers if g.late]

    # select query
    extr_vars = {}
    term = request.vars.term or ""

    if not term:
        rows = registers[regs * (page - 1) : regs * page]
    else:
        rows = [
            reg
            for reg in registers
            if term.lower() in reg.guesid.name_sa.lower()
        ][regs * (page - 1) : regs * page]

    for reg in rows:
        reg.guest_name = reg.guesid.name
        if reg.lodge == "LDG" and reg.bedroom:
            reg.bedroom_name = reg.bedroom.bedroom
            reg.bedroom_building = reg.bedroom.builid.building
        elif reg.lodge == "LDG" and not reg.bedroom:
            reg.bedroom = "unalloc"
        else:
            reg.bedroom = None
        reg.age = (
            (date.today() - reg.guesid.birthday).days // 365
            if reg.guesid.birthday
            else 0
        )

    return dict(
        event=event,
        rows=rows,
        event_records=len(ids),
        lates=lates,
        page=page,
        term=term,
        total_registers=total_registers,
        admin_view=admin_view,
        view_credits=view_credits,
    )


# delete
@auth.requires_login()
@auth.requires(auth.has_membership("root") or auth.has_membership("admin"))
def delete():
    evenid = int(request.args(0)) or redirect(URL("list"))
    if db(Register.evenid == evenid).select():
        event = Events[evenid]
        event.update_record(is_active=False)
        mapp = db(Bedrooms_mapping.evenid == evenid).select().first()
        mapp.update_record(is_active=False)
        return "window.location = document.referrer;"
    else:
        db(Events.id == evenid).delete()
        db(Bedrooms_mapping.evenid == evenid).delete()
        return 'location.href="%s";' % URL("events", "list")


# event status (on / off)
@auth.requires_login()
@auth.requires(auth.has_membership("root") or auth.has_membership("admin"))
def event_on_off():
    event = Events[request.vars.evenid]
    if event.status == "OPN":
        event.update_record(status="CLS")
    else:
        event.update_record(status="OPN")
    return "document.location.reload(true)"


#  forms  #####################################################################
def _event_form(instance=None):
    form = (
        SQLFORM(Events, instance, submit_button=T("Update"))
        if instance
        else SQLFORM(Events, submit_button=T("Add"))
    )

    if auth.has_membership("admin"):
        form.element(_id="events_center__row")["_style"] = "display:none;"
        form.element("option", _value=int(auth.user.center))[
            "_selected"
        ] = "selected"

    form.element(_type="submit")["_class"] = "btn btn-primary btn-lg"
    form.element(_name="description")["_rows"] = 2
    form.element(_id="submit_record__row")["_class"] = "mt-3 text-end"
    submit_class = "btn btn-outline-{} btn-lg mb-4".format(
        "secondary" if instance else "primary"
    )
    form.element(_type="submit")["_class"] = submit_class

    if instance:
        form.element(_id="events_id__row")["_class"] = "d-none"

    return form
