openerp.grp_ceip_distribucion = function (instance) {
    instance.web.ActionManager = instance.web.ActionManager.extend({

        ir_actions_act_close_wizard_and_reload_view: function (action, options) {
            if (!this.dialog) {
                options.on_close();
            }
            this.dialog_stop();
            this.inner_widget.views[this.inner_widget.active_view].controller.reload();
            return $.when();
        },
    });
}