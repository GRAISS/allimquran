frappe.listview_settings['ALLIM Trial Lesson Request'] = {
  add_fields: ['status','trial_coordinator','trial_follow_up'],
  get_indicator(doc) {
    const colors = {New:'orange',Contacted:'blue',Scheduled:'blue',Reschedule:'orange','No Show':'red',Completed:'green',Enrolled:'green',Closed:'gray'};
    return [__(doc.status), colors[doc.status] || 'gray', 'status,=,' + doc.status];
  },
  onload(list) {
    list.page.add_inner_button(__('Needs follow-up'), () => {
      list.filter_area.clear();
      list.filter_area.add([['ALLIM Trial Lesson Request','status','not in',['Closed','Enrolled']],
        ['ALLIM Trial Lesson Request','trial_follow_up','<=',frappe.datetime.now_datetime()]]);
    });
    list.page.add_inner_button(__('Unassigned requests'), () => {
      list.filter_area.clear();
      list.filter_area.add([['ALLIM Trial Lesson Request','status','not in',['Closed','Enrolled']],
        ['ALLIM Trial Lesson Request','trial_coordinator','is','not set']]);
    });
  }
};
