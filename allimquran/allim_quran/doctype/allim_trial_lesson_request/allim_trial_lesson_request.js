frappe.ui.form.on('ALLIM Trial Lesson Request', {
  refresh(frm) {
    if (frm.is_new()) return;
    const field = name => {
      const df = frm.get_docfield(name);
      return {fieldname:name, fieldtype:df.fieldtype, label:__(df.label), options:df.options, default:frm.doc[name], reqd:true};
    };
    const action = (label, status, names) => {
      frm.add_custom_button(__(label), () => {
        if (frm.is_dirty()) {
          frappe.msgprint(__('Save your changes before taking this action.')); return;
        }
        const dialog = new frappe.ui.Dialog({title:__(label), fields:names.map(field),
          primary_action_label:__('Save'),
          async primary_action(values) {
            const button = dialog.get_primary_btn(); button.prop('disabled', true);
            try {
              await frm.set_value({...values, status});
              await frm.save(); dialog.hide();
            } catch (_) {
              frappe.show_alert({message:__('The request was not saved. Review the fields and try again.'),indicator:'red'});
            } finally { button.prop('disabled', false); }
          }});
        dialog.show();
      }, __('Trial lesson'));
    };
    const status = frm.doc.status;
    if (['New','Reschedule','No Show'].includes(status))
      action('Contacted', 'Contacted', ['trial_coordinator','trial_follow_up']);
    if (['New','Contacted','Scheduled','Reschedule','No Show'].includes(status))
      action('Schedule trial lesson', 'Scheduled', ['trial_coordinator','trial_teacher','trial_start','trial_timezone','trial_duration','trial_meeting_url']);
    if (status === 'Scheduled') {
      action('Record lesson result', 'Completed', ['trial_coordinator','trial_teacher','trial_completed_at','trial_result','trial_recommendation','trial_next_step','trial_follow_up']);
      action('Reschedule', 'Reschedule', ['trial_coordinator','trial_reason','trial_follow_up']);
      action('No Show', 'No Show', ['trial_coordinator','trial_reason','trial_follow_up']);
    }
    if (status === 'Completed' && frm.get_docfield('student_user') && frm.get_docfield('learning_group'))
      action('Confirm enrollment', 'Enrolled', ['student_user','learning_group']);
    if (!['Closed','Enrolled'].includes(status)) action('Close request', 'Closed', ['trial_reason']);
    frm.add_custom_button(__('Notification history'), () => frappe.set_route('List','ALLIM Trial Notice',{trial_request:frm.doc.name}), __('Trial lesson'));
    if (!frm.doc.trial_coordinator) frm.dashboard.set_headline_alert(__('Choose a trial coordinator.'));
    else if (!['Closed','Enrolled'].includes(status) && frm.doc.trial_follow_up && frappe.datetime.get_diff(frappe.datetime.now_datetime(),frm.doc.trial_follow_up)>0)
      frm.dashboard.set_headline_alert(__('The follow-up deadline has passed. Record the next action.'));
  }
});
