from xml.dom.minidom import Element
from gluon.custom_import import track_changes
import Mapp_Utils as Mapp
from datetime import date

track_changes(True)


#  buildings on event  ########################################################
@auth.requires_login()
@auth.requires(
    auth.has_membership("root")
    or auth.has_membership("admin")
    or auth.has_membership("office")
)
def buildings_on_event():
    # if exists session.mapping delete it
    if session.mapping:
        clear_session()
    # geting event to render details
    event = Events[request.vars.evenid]
    # init a new mapping
    Mapp.init_mapp(
        evenid=int(event.id),
        centid=int(event.center),
        cent_repr=(center_repr % event.center),
    )
    # get bedrooms
    bedrooms = db(Bedroom.id.belongs(session.mapp.ids_in_mapping)).select(
        orderby=Bedroom.builid
    )
    Mapp.compare_mapping_and_bedrooms(bedrooms)
    for bedroom in bedrooms:
        bedroom.mapp = Mapp.add_mapp(bedroom.id)
    # making buildings
    buildings = db(
        Building.id.belongs(set([bed.builid for bed in bedrooms]))
    ).select()
    for building in buildings:
        building.male = Mapp.gen_mapp_buildings(
            [
                bed
                for bed in bedrooms
                if bed.gender == "M" and bed.builid == building.id
            ]
        )
        building.female = Mapp.gen_mapp_buildings(
            [
                b
                for b in bedrooms
                if b.gender == "F" and b.builid == building.id
            ]
        )
        building.mixed = Mapp.gen_mapp_buildings(
            [
                b
                for b in bedrooms
                if b.gender == "X" and b.builid == building.id
            ]
        )
    unalloc = True if len(session.mapp.unallocateds) else False

    return dict(rows=buildings, event=event, unalloc=unalloc)


#  building on event  #########################################################
@auth.requires_login()
@auth.requires(
    auth.has_membership("root")
    or auth.has_membership("admin")
    or auth.has_membership("office")
)
def building_on_event():
    # verifying if session.mapp exists
    if not session.mapp:
        redirect(URL("events", "show", vars={"evenid": request.vars.evenid}))
    # geting event to render details
    event = Events[request.vars.evenid]
    # get bedrooms
    bedrooms = db(
        (Bedroom.id.belongs(session.mapp.ids_in_mapping))
        & (Bedroom.builid == request.vars.builid)
    ).select(orderby=Bedroom.builid)
    for bedroom in bedrooms:
        bedroom.mapp = Mapp.add_mapp(bedroom.id)
    # geting the building
    building = Building[request.vars.builid]
    building.male = Mapp.gen_mapp_building(
        [b for b in bedrooms if b.gender == "M"]
    )
    building.female = Mapp.gen_mapp_building(
        [b for b in bedrooms if b.gender == "F"]
    )
    building.mixed = Mapp.gen_mapp_building(
        [b for b in bedrooms if b.gender == "X"]
    )
    unalloc = True if len(session.mapp.unallocateds) else False

    return dict(building=building, event=event, unalloc=unalloc)


#  List (by gender)  ##########################################################
@auth.requires_login()
@auth.requires(
    auth.has_membership("root")
    or auth.has_membership("admin")
    or auth.has_membership("office")
)
def bedrooms_by_gender_on_event():
    # verifying if session.mapp exists
    if not session.mapp:
        redirect(URL("events", "show", vars={"evenid": request.vars.evenid}))
    # geting event to render details
    event = Events[request.vars.evenid]
    # get bedrooms
    _bedrooms = db(
        (Bedroom.id.belongs(session.mapp.ids_in_mapping))
        & (Bedroom.builid == request.vars.builid)
        & (Bedroom.gender == request.vars.gender)
    ).select(orderby=~Bedroom.floor_room | Bedroom.bedroom)
    # create a dict of bedrooms with mapp
    bedrooms = []
    for bedroom in _bedrooms:
        bedroom.in_use = Mapp.gen_mapp_gender(
            bedroom, Mapp.add_mapp(bedroom.id)
        )
        bedrooms.append(Mapp.icons_mapp(bedroom))
    # verify unallocates
    unallocateds = Mapp.unallocateds_by_gender(request.vars.gender)
    unalloc = True if len(unallocateds) else False

    return dict(
        rows=bedrooms,
        event=event,
        gender=request.vars.gender,
        builid=_bedrooms[0].builid,
        unalloc=unalloc,
    )


#  bedroom on event  ##########################################################
@auth.requires_login()
@auth.requires(
    auth.has_membership("root")
    or auth.has_membership("admin")
    or auth.has_membership("office")
)
def bedroom_on_event():
    # verifying if session.mapp exists
    if not session.mapp:
        redirect(URL("events", "show", vars={"evenid": request.vars.evenid}))
    # geting event to render details
    event = Events[request.vars.evenid]
    # get mapp
    mapp = [
        m for m in session.mapp.mapping if m[0] == int(request.vars.bedroomid)
    ][0]
    # update bedroom with mapp
    bedroom = Bedroom[int(request.vars.bedroomid)]
    bedroom.beds = mapp[1]
    bedroom.tops = mapp[2]
    # creating a dict of name
    _ids = filter((lambda x: x != 0), (mapp[1] + mapp[2]))
    guests = {
        r.guesid: dict(
            name=shortname(r.guesid.name),
            no_stairs=r.no_stairs,
            no_top_bunk=r.no_top_bunk,
            age=(date.today() - r.guesid.birthday).days // 365
            if r.guesid.birthday
            else 0,
        )
        for r in db(Register.guesid.belongs(_ids)).select()
    }
    # verify unallocates
    unallocateds = Mapp.unallocateds_by_gender(request.vars.gender)
    unalloc = True if len(unallocateds) else False

    return dict(
        bedroom=bedroom,
        guests=guests,
        event=event,
        building=[bedroom.builid, bedroom.builid.building],
        unalloc=unalloc,
    )


#  get unallocateds  ##########################################################
def get_unallocateds():
    response.view = "accommodations/modal_unallocateds.html"
    gender = request.vars.gender
    add = True if request.vars.add else False
    unallocateds = Mapp.unallocateds_by_gender(gender)
    unallocateds.sort(key=lambda r: r["name"])

    return dict(add=add, unallocateds=unallocateds)


#  allocate all  ##############################################################
@auth.requires_login()
@auth.requires(auth.has_membership("root") or auth.has_membership("admin"))
def allocate_all():
    # receiving the variables
    evenid = session.mapp.evenid
    event_type = Events[evenid].activity.activity_type
    mapping = db(Bedrooms_mapping.evenid == evenid).select().first()
    bedrooms = [b for b in session.mapp.mapping if 0 in (b[1] + b[2])]
    # sub-lists
    _no_stairs = [b for b in bedrooms if b[4] == 0 and 0 in b[1]]
    _no_top_bunk = sorted(
        [b for b in bedrooms if 0 in b[1]], key=lambda x: x[4], reverse=True
    )
    _no_problems = sorted(bedrooms, key=lambda x: x[4], reverse=True)
    # unallocateds
    guests = session.mapp.unallocateds
    # put each guest on a bedroom
    allocateds, unallocateds = [], []
    for guest in guests:
        if guest["gender"] == "M":
            if guest["no_stairs"]:
                _bedrooms = [b for b in _no_stairs if b[3] == "M"]
            elif guest["no_top_bunk"] or guest["age"] >= 60:
                _bedrooms = [b for b in _no_top_bunk if b[3] == "M"]
            else:
                _bedrooms = [b for b in _no_problems if b[3] == "M"]
        elif guest["gender"] == "F":
            if guest["no_stairs"]:
                _bedrooms = [b for b in _no_stairs if b[3] == "F"]
            elif guest["no_top_bunk"] or guest["age"] >= 60:
                _bedrooms = [b for b in _no_top_bunk if b[3] == "F"]
            else:
                _bedrooms = [b for b in _no_problems if b[3] == "F"]
        allocate = Mapp.put_on_a_bedroom(guest, _bedrooms)
        if allocate:
            allocateds.append(allocate)
            register = Register[guest["regid"]]
            register.update_record(bedroom=allocate[2])
            guest_stay = (
                db(
                    (Guest_Stay.guesid == guest["id"])
                    & (Guest_Stay.center == session.mapp.centid)
                )
                .select()
                .first()
            )
            if event_type == "SCF":
                guest_stay.update_record(bedroom_alt=allocate[2])
            else:
                guest_stay.update_record(bedroom=allocate[2])
        else:
            unallocateds.append([guest["id"], guest["name"]])
    mapping.update_record(bedrooms=session.mapp.mapping)

    return dict(
        evenid=evenid,
        allocateds=sorted(allocateds, key=lambda x: x[1]),
        unallocateds=sorted(unallocateds, key=lambda x: x[1]),
    )


#  add to bedroom  ############################################################
@auth.requires_login()
@auth.requires(
    auth.has_membership("root")
    or auth.has_membership("admin")
    or auth.has_membership("office")
)
def add_to_bedroom():
    # receiving the variables
    regid = int(request.vars.regid)
    evenid = int(request.vars.evenid)
    guesid = int(request.vars.guesid)
    gender = request.vars.gender
    bedroomid = int(request.vars.bedroomid)
    from_mapp = False if request.vars.fromguest else True
    # try to allocate
    try_to_allocate = Mapp.choose_a_bed(
        evenid, guesid, bedroomid, regid, from_mapp
    )

    if try_to_allocate:
        url = (
            URL("events", "show", vars={"evenid": evenid, "admin_view": "T"})
            if request.vars.fromguest
            else URL(
                "bedroom_on_event",
                vars={
                    "bedroomid": bedroomid,
                    "evenid": evenid,
                    "gender": gender,
                },
            )
        )
        if request.vars.fromguest:
            redirect(url)
        else:
            return f"location.href='{url}'"
    else:
        return "window.alert('crowded bedroom');"


#  remove from bedroom  #######################################################
@auth.requires_login()
@auth.requires(
    auth.has_membership("root")
    or auth.has_membership("admin")
    or auth.has_membership("office")
)
def remove_from_bedroom():
    # receiving the variables
    evenid = int(request.vars.evenid)
    guesid = int(request.vars.guesid)
    bedroomid = int(request.vars.bedroomid)
    # select event and type
    event = Events[evenid]
    event_type = event.activity.activity_type
    # select guest stay
    guest_stay = (
        db((Guest_Stay.guesid == guesid) & (Guest_Stay.center == event.center))
        .select()
        .first()
    )
    # select register
    register = (
        db(
            (Register.guesid == guesid)
            & (Register.evenid == evenid)
            & (Register.is_active == True)
            & (Register.credit == False)
        )
        .select()
        .first()
    )
    # select mapping in DB
    mapping = db(Bedrooms_mapping.evenid == evenid).select().first()
    bedroom = [mapp for mapp in mapping["bedrooms"] if mapp[0] == bedroomid][0]
    # remove guest from bedroom
    if guesid in bedroom[1]:
        bedroom[1].remove(guesid)
        bedroom[1].append(0)
    elif guesid in bedroom[2]:
        bedroom[2].remove(guesid)
        bedroom[2].append(0)
    # update DB(s)
    mapping.update_record(bedrooms=mapping["bedrooms"])
    if register:
        register.update_record(bedroom=None)
    if event_type == "SCF":
        guest_stay.update_record(bedroom_alt=None)
    else:
        guest_stay.update_record(bedroom=None)

    if request.vars.fromguest:
        return "..."
    else:
        # re-init the Mapp
        Mapp.init_mapp(
            evenid=int(event.id),
            centid=session.mapp.centid,
            cent_repr=session.mapp.cent_repr,
        )
        return "location.href='{}';".format(
            URL(
                "bedroom_on_event",
                vars={
                    "bedroomid": bedroomid,
                    "evenid": evenid,
                    "gender": register.guesid.gender,
                },
            )
        )


#  guest bedroom  ####
@auth.requires_login()
@auth.requires(auth.has_membership("root") or auth.has_membership("admin"))
def guest_bedroom():
    # get vars
    evenid = int(request.vars.evenid)
    guesid = int(request.vars.guesid)
    # try to get the guest bedroom
    bedroom = get_bedroom(evenid, guesid)

    if bedroom:
        response.view = "accommodations/modal_guest_on_bedroom.html"
        # set title of report
        title = "{} - {}".format(
            Bedroom[bedroom[0]].builid.building, bedroom[5]
        )
        # select guests in bedroom
        _ids = [id for id in bedroom[1] + bedroom[2] if id != 0]
        guests = {g.id: g.name for g in db(Guest.id.belongs(_ids)).select()}
        # adjust guests on beds or tops
        beds, tops = [], []
        for gid in bedroom[1]:
            beds.append((gid, guests[gid]) if gid != 0 else 0)

        for gid in bedroom[2]:
            tops.append((gid, guests[gid]) if gid != 0 else 0)

        return dict(
            title=title,
            beds=beds,
            tops=tops,
            evenid=evenid,
            guesid=guesid,
            bedroomid=bedroom[0],
        )

    else:
        # select the view
        response.view = "accommodations/modal_guest_to_bedroom.html"
        # get title
        title = T("Select a bedroom")
        # get mapping
        mapping = db(Bedrooms_mapping.evenid == int(evenid)).select().first()
        # get register
        register = (
            db(
                (Register.guesid == guesid)
                & (Register.evenid == evenid)
                & (Register.is_active == True)
                & (Register.credit == False)
            )
            .select()
            .first()
        )
        # select possible bedrooms by gender
        if register.guesid.gender == "M":
            bed_per_gender = [
                bed
                for bed in mapping["bedrooms"]
                if bed[3] in ("M", "X") and 0 in (bed[1] + bed[2])
            ]
        else:
            bed_per_gender = [
                bed
                for bed in mapping["bedrooms"]
                if bed[3] in ("F", "X") and 0 in (bed[1] + bed[2])
            ]
        # and by restrictions
        if register.no_top_bunk and register.no_stairs:
            possible_bedrooms = [
                bed for bed in bed_per_gender if bed[4] == 0 and 0 in bed[1]
            ]
        elif register.no_top_bunk or get_age(register.guesid.birthday) >= 60:
            possible_bedrooms = [bed for bed in bed_per_gender if 0 in bed[1]]
        else:
            possible_bedrooms = bed_per_gender
        # select vacancies
        pbids = [pb[0] for pb in possible_bedrooms]  # possible bedrooms ids
        _vacancies = db(Bedroom.id.belongs(pbids)).select()
        VACANCIES = dict()
        for vac in _vacancies:
            VACANCIES[int(vac.id)] = "{}({}) - {}({}) [{}B {}T]".format(
                vac.builid.building,
                vac.builid.center.shortname,
                vac.bedroom,
                GENDER_BEDROOM[vac.gender],
                vac.beds,
                vac.top_bunks,
            )
        # generate a form to show vacancies
        form = SQLFORM.factory(
            Field(
                "bedroomid",
                requires=IS_IN_SET(VACANCIES),
                label=T("select a bedroom"),
            ),
            hidden=dict(
                evenid=evenid,
                guesid=guesid,
                gender=register.guesid.gender,
                regid=register.id,
                fromguest=True,
            ),
            formstyle="bootstrap4_stacked",
            submit_button="select",
        )
        form.element(_type="submit")[
            "_class"
        ] = "btn btn-outline-primary float-end mt-2"
        form.element("form")["_class"] = ""
        form.element("form")["_action"] = URL(
            "accommodations", "add_to_bedroom"
        )

        return dict(title=title, form=form)
