
openerp.readonly_fields = function (instance) {

	var _t = openerp.web._t,
        _lt = openerp.web._lt;
    var QWeb = openerp.web.qweb;

    openerp.web.FormView.include({
        _process_save: function(save_obj) {
        var self = this;
        var prepend_on_create = save_obj.prepend_on_create;
        try {
            var form_invalid = false,
                values = {},
                first_invalid_field = null,
                readonly_values = {};
            for (var f in self.fields) {
                if (!self.fields.hasOwnProperty(f)) { continue; }
                f = self.fields[f];
                if (!f.is_valid()) {
                    form_invalid = true;
                    if (!first_invalid_field) {
                        first_invalid_field = f;
                    }
                } else if (f.name !== 'id' && (!self.datarecord.id || f._dirty_flag)) {
                    // Special case 'id' field, do not save this field
                    // on 'create' : save all non readonly fields
                    // on 'edit' : save non readonly modified fields
                    if (!f.get("readonly") || (f.options && f.options.save_readonly)) {
                        values[f.name] = f.get_value();
                    } else {
                        readonly_values[f.name] = f.get_value();
                    }
                }
            }

            if (form_invalid) {
                self.set({'display_invalid_fields': true});
                first_invalid_field.focus();
                self.on_invalid();
                return $.Deferred().reject();
            } else {
                self.set({'display_invalid_fields': false});
                var save_deferral;
                if (!self.datarecord.id) {
                    // Creation save
                    save_deferral = self.dataset.create(values, {readonly_fields: readonly_values}).then(function(r) {
                        return self.record_created(r, prepend_on_create);
                    }, null);
                } else if (_.isEmpty(values)) {
                    // Not dirty, noop save
                    save_deferral = $.Deferred().resolve({}).promise();
                } else {
                    // Write save
                    save_deferral = self.dataset.write(self.datarecord.id, values, {readonly_fields: readonly_values}).then(function(r) {
                        return self.record_saved(r);
                    }, null);
                }
                return save_deferral;
            }
        } catch (e) {
            console.error(e);
            return $.Deferred().reject();
        }
    },
    });
    
};

