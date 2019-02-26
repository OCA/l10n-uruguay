view_list_inherit = function(instance) {
    var _t = instance.web._t,
    _lt = instance.web._lt;
    var QWeb = instance.web.qweb;

    instance.web.View.include({
        load_view: function(context) {
            var self = this;

            if (!this.options.new_window && this.view_type=='tree' && !(this.dataset && this.dataset.parent_view) && !this.m2m_field){
                var function_exec = new instance.web.Model('show.fields').get_func('action')({ 'model_name': self.model,
                                                                           'user_id': self.session.uid,
                                                                           'view_id': this.view_id,
                                                                           'view_type': this.view_type,
                                                                          }, 'select', self.dataset.get_context());
                return function_exec.then(function(result){
                    self.result = result;

                    var view_loaded_def;

                    if (self.embedded_view) {
                        view_loaded_def = $.Deferred();
                        $.async_when().done(function() {
                            view_loaded_def.resolve(self.embedded_view);
                        });
                    }else {
                        if (! self.view_type){
                            console.warn("view_type is not defined", self);
                            }
                        view_loaded_def = instance.web.fields_view_get({
                            "model": self.dataset._model,
                            "view_id": self.view_id,
                            "view_type": self.view_type,
                            "toolbar": !!self.options.$sidebar,
                            "context": self.dataset.get_context(),
                        });
                    }

                    return self.alive(view_loaded_def).then(function(r) {
                        self.fields_view = r;
                        self.render_fields_show();
                        // add css classes that reflect the (absence of) access rights
                        self.$el.addClass('oe_view')
                            .toggleClass('oe_cannot_create', !self.is_action_enabled('create'))
                            .toggleClass('oe_cannot_edit', !self.is_action_enabled('edit'))
                            .toggleClass('oe_cannot_delete', !self.is_action_enabled('delete'));
                        return $.when(self.view_loading(r)).then(function() {
                            self.trigger('view_loaded', r);
                        });
                    });
                });

            }else{

                var view_loaded_def;

                if (self.embedded_view) {
                    view_loaded_def = $.Deferred();
                    $.async_when().done(function() {
                        view_loaded_def.resolve(self.embedded_view);
                    });
                }else {
                    if (! self.view_type){
                        console.warn("view_type is not defined", self);
                        }
                    view_loaded_def = instance.web.fields_view_get({
                        "model": self.dataset._model,
                        "view_id": self.view_id,
                        "view_type": self.view_type,
                        "toolbar": !!self.options.$sidebar,
                        "context": self.dataset.get_context(),
                    });
                }

                return self.alive(view_loaded_def).then(function(r) {
                    self.fields_view = r;
                    // add css classes that reflect the (absence of) access rights
                    self.$el.addClass('oe_view')
                        .toggleClass('oe_cannot_create', !self.is_action_enabled('create'))
                        .toggleClass('oe_cannot_edit', !self.is_action_enabled('edit'))
                        .toggleClass('oe_cannot_delete', !self.is_action_enabled('delete'));
                    return $.when(self.view_loading(r)).then(function() {
                        self.trigger('view_loaded', r);
                    });
                });
            }
        },
        render_fields_show: function () {
            var self = this;
            if (this.fields_view.type == 'tree' && typeof(this.result) != 'undefined'){
                    if ((this.dataset && this.dataset.parent_view) || this.m2m_field){
                        self.data = { show_button_col: false };
                        return;
                    }

                    String.prototype.replaceAll = function(target, replacement) { return this.split(target).join(replacement); }; // TODO: analize this! Remove?
                    var show_button_col = this.result.show_button_col;
                    var data_show_field = this.result.data || {};
                    self.data_show_field = data_show_field;
                    var all_fields_of_model = this.result.fields || {};
                    self.all_fields_of_model = all_fields_of_model;

                    this._visible_columns = _.filter(this.fields_view.arch.children, function (column) { return column.tag=='field' && column.attrs.invisible != '1' && (!column.attrs.modifiers || JSON.parse(column.attrs.modifiers).tree_invisible!=true || JSON.parse(column.attrs.modifiers).tree_invisible!='1') });

                    var field_visible = data_show_field.hasOwnProperty('fields_show') && data_show_field['fields_show'] ? eval(data_show_field['fields_show'].replaceAll("u'", "'")) : _.pluck(_.pluck(self._visible_columns, 'attrs'), 'name');
                    var fields_sequence = data_show_field.hasOwnProperty('fields_sequence') && data_show_field['fields_sequence'] ? JSON.parse(data_show_field['fields_sequence']) : {};
                    var fields_string = {};
                    if (data_show_field.hasOwnProperty('fields_string') && data_show_field['fields_string']){
                        fields_string = JSON.parse(data_show_field['fields_string']);
                    }else{
                        for(var i=0; i < self._visible_columns.length; i++){
                            var f = self._visible_columns[i];
                            if(f.attrs.string){
                                fields_string[f.attrs.name] = f.attrs.string;
                            }
                        }
                    }

                    var list_data = [];
                    if (show_button_col){
                        var sequence = 5;
                        // Adicionar primero los campos visibles
                        for(var i=0; i < field_visible.length; i++){
                            var field_name = field_visible[i];
                            if (!all_fields_of_model.hasOwnProperty(field_name)){ continue; }
                            var field_obj = all_fields_of_model[field_name];
                            var data = {value: field_name, string: field_obj.string, sequence: sequence, checked: 'checked' }
                            sequence += 5;
                            if (fields_sequence.hasOwnProperty(field_name)){
                               data['sequence'] = fields_sequence[field_name];
                            }
                            if (fields_string.hasOwnProperty(field_name)){
                                data['string'] = fields_string[field_name];
                            }
                            list_data.push(data);
                        }

                        var all_fields_of_model_sorted = _.sortBy(_.pairs(all_fields_of_model), function (f){ return f[1].string || 'zzz'; });
                        for (var index in all_fields_of_model_sorted){
                            var field_name = all_fields_of_model_sorted[index][0];
                            if (field_visible.indexOf(field_name) >= 0){
                                continue;
                            }
                            var field_obj = all_fields_of_model_sorted[index][1];
                            var data = {value: field_name, string: field_obj.string }
                            list_data.push(data);
                        }
                        list_data = _.sortBy(list_data, function (o){return o.sequence });
                    }

                    self.data = { show_button_col: show_button_col, show_all_user: this.result.show_all_user, all_user_checked: data_show_field.all_user, suggestion: list_data, attrs: {color: data_show_field.color || 'check-primary'}};

                    if (!(_.isEmpty(data_show_field))){
                        var field = {}, children = [], _fields_show = [];
                        for (var idx in field_visible){
                            var _field = field_visible[idx];
                            _fields_show.push({'value': _field, 'sequence': fields_sequence[_field] || 100});
                        }
                        _fields_show = _.sortBy(_fields_show, function (o){return o.sequence});

                        var _fields = self.fields_view.fields;
                        var _children = self.fields_view.arch.children;

                        var fields_modifiers = [];
                        var attr_names = _.keys(self.fields_view.arch.attrs);
                        var field_names = _.keys(_fields);
                        for (var i in attr_names){
                            var attr_name = attr_names[i];
                            if (attr_name == 'colors' || attr_name.startsWith("decoration")){
                                var attr_value = self.fields_view.arch.attrs[attr_name];
                                for (var idx in field_names){
                                    var f_name = field_names[idx];
                                    if (attr_value.indexOf(f_name) !== -1){
                                        fields_modifiers.push(f_name);
                                    }
                                }
                            }
                        }

                        for (var _field in _fields_show){
                            _field = _fields_show[_field];

                            var child = undefined;
                            for(var i=0; i < _children.length; i++){
                                if (_children[i].attrs.name == _field.value){
                                    child = JSON.parse(JSON.stringify(_children[i]));
                                    if ((child.attrs.hasOwnProperty('invisible') && (child.attrs.invisible=='1' || child.attrs.invisible==true)) || (child.attrs.hasOwnProperty('modifiers') && (JSON.parse(child.attrs.modifiers).tree_invisible==true || JSON.parse(child.attrs.modifiers).tree_invisible=='1'))){
                                        delete child.attrs.invisible;
                                        child.attrs.modifiers = "";
                                        _children[i].already_include = true;
                                    }else{
                                        if (child.attrs.hasOwnProperty('modifiers')){
                                            var _attrs_mod = JSON.parse(child.attrs.modifiers);
                                            for (var attr in _attrs_mod){
                                                if(_.isArray(_attrs_mod[attr])){
                                                    for (var i in _attrs_mod[attr]){
                                                        if(_.isArray(_attrs_mod[attr][i]) && _attrs_mod[attr][i].length===3 && _.contains(fields_modifiers, _attrs_mod[attr][i][0])===false)
                                                            fields_modifiers.push(_attrs_mod[attr][i][0])
                                                    }
                                                }
                                            }
                                        }
                                    }
                                    break;
                                }
                            }
                            if (!child){
                                child = { attrs: {modifiers: "", name: _field.value}, children: [], tag: "field" }
                            }
                            if (fields_string.hasOwnProperty(child.attrs.name)){
                                child.attrs.string = fields_string[child.attrs.name];
                            }
                            children.push(child);

                            var f = _fields.hasOwnProperty(_field.value) ? _fields[_field.value] : all_fields_of_model[_field.value];
                            if (f && fields_string.hasOwnProperty(_field.value)){
                                f.string = fields_string[_field.value];
                            }
                            if (f){
                                field[_field.value] = f;
                            }
                        }

                        // prepare children
                        for (var index in _children){
                            var _field = _children[index];
                            if (_field.tag=='field' && !_field.already_include && _field.attrs.invisible == '1'){
                                field[_field.attrs.name] = all_fields_of_model[_field.attrs.name]
                                children.push(_field);
                            }
                            if (_field.tag !== 'field'){
                                // Buscar si se encuentra el campo anterior al botón
                                // si no se encuentra colocarlo al final
                                if (index===0){
                                    children.splice(0, 0, _field);
                                }else{
                                    var inserted = false;
                                    var _previous_visible_child_name = '';
                                    for(var j=index-1; j >= 0; j--){
                                        if (_children[j].tag=='field' && (!_children[j].attrs.invisible || _children[j].attrs.invisible !== '1')){
                                            _previous_visible_child_name = _children[j].attrs.name;
                                            break;
                                        }
                                    }
                                    if (_previous_visible_child_name){
                                        for(var k=0; k < children.length; k++){
                                            if (children[k].attrs.name == _previous_visible_child_name){
                                                children.splice(k+1, 0, _field);
                                                inserted = true;
                                                break
                                            }
                                        }
                                    }
                                    if(!inserted){
                                        children.push(_field);
                                    }
                                }
                            }
                        }
                        if(fields_modifiers.length > 0){
                            var added_field_names = _.keys(field);
                            for (var idx in fields_modifiers){
                                var f_name = fields_modifiers[idx];
                                if(_.contains(added_field_names, f_name)===false){
                                    field[f_name] = all_fields_of_model[f_name];
                                    children.push({ attrs: {invisible: '1', modifiers: '{"readonly": true, "tree_invisible": true}', name: f_name}, children: [], tag: "field" });
                                }
                            }
                        }

                        self.fields_view.fields = field;
                        self.fields_view.arch.children = children;
                    }
            }
        }
    });

   instance.web.ListView.include({
        load_list: function(data) {
            this._super(data);
            this.add_events_fields_container();
        },
        add_events_fields_container: function(){

            if (typeof(this.ok) == "undefined"){
                this.ok = false;
            }

            if (this.$buttons && !this.ok) {
                this.ok = true;
                this.$buttons.find(".toggle_select_field").click(function() {
                    $(this).next().toggle();
                });
                this.$buttons.find(".sequence").change(function () {
                    $(this).parents('.setting_field').next('input').attr({'sequence': $(this).val()});
                });
                this.$buttons.find(".string_field").change(function () {
                    $(this).parents('.setting_field').next('input').attr({'string_field': $(this).val()});
                });
                this.$buttons.find("i[setting]").click(function () {
                    $(this).parent().find('.setting_field').toggle();
                });
                this.$buttons.find(".update_setting_field").click(function () {
                    var parent = $(this).parents('.setting_field');
                    parent.next().attr({string_field: parent.find('.string_field').val(), 'sequence': parent.find('.sequence').val()})
                    parent.toggle();
                });

                this.$buttons.find(".item_label_field").click(function () {
                    var $input = $(this).closest('li').find('input[type="checkbox"]');
                    $input.prop("checked", !$input.prop("checked"));
                });

                this.update_show_fields(this.$buttons);
           }
        },
        update_show_fields: function (node) {
            var self = this;
            if (typeof(node) != 'undefined'){
                node.find('a[action="update"]').click(function () {
                    var fields = []
                    var sequence = {}
                    var fields_string = {}
                    self.$buttons.find('.choose_field_show').find('.suggestion input:checked').each(function () {
                        fields.push($(this).val());
                        var _seq = $(this).attr('sequence') || false;
                        if (_seq){
                            sequence[$(this).attr('id')] = parseInt(_seq);
                        }
                        var _str = $(this).attr('string_field') || false;
                        if (_str){
                            fields_string[$(this).attr('id')] = _str;
                        }
                    });
                    var all_users = self.$buttons.find('.choose_field_show').find('#all_user').is(':checked');
                    new instance.web.Model('show.fields').call('action', [{'model_name': self.model, 'fields_show': fields,
                                'user_id': self.session.uid, 'fields_sequence': JSON.stringify(sequence), 'all_user': all_users,
                                'fields_string': JSON.stringify(fields_string), 'view_id': self.view_id, 'view_type': 'tree' }, 'update', self.dataset.get_context() ]).then(function (result) {
                        self.$buttons.find('div.text_suggestion').hide();
                        self.load_view(self.dataset.get_context()).then(function() {
                            self.reload_content();
                            var $div_buttons = $(QWeb.render("ListView.buttons", {'widget':self}));
                            self.$buttons.find('div.choose_field_show').replaceWith($div_buttons.find('div.choose_field_show'));
                            self.ok = false;
                            self.add_events_fields_container();
                        });
                    });
                });

                node.find('a[action="reset"]').click(function () {
                    new instance.web.Model('show.fields').call('action', [{'model_name': self.model,
                                'user_id': self.session.uid, 'view_id': self.view_id, 'view_type': 'tree' }, 'delete', self.dataset.get_context() ]).then(function (result) {
                        self.$buttons.find('div.text_suggestion').hide();
                        self.load_view(self.dataset.get_context()).then(function() {
                            self.reload_content();
                            var $div_buttons = $(QWeb.render("ListView.buttons", {'widget':self}));
                            self.$buttons.find('div.choose_field_show').replaceWith($div_buttons.find('div.choose_field_show'));
                            self.ok = false;
                            self.add_events_fields_container();
                        });
                    });
                });
            }
        }
    });
};

openerp.dynamic_listview_advance = function(instance) {
    view_list_inherit(instance);
};
