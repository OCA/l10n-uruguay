/*---------------------------------------------------------
 * Odoo v8 custom group by
 *---------------------------------------------------------*/
openerp.search_view_custom_group = function(instance, module) {

    var QWeb = instance.web.qweb,
        _t =  instance.web._t;

instance.web.search.CustomGroupBy = instance.web.search.Input.extend({
    _in_drawer: true,
    start: function () {
        var self = this;
        this.group_fields=[];
        this.$el
            .on('keypress keydown keyup', function (e) { e.stopPropagation(); })
            .on('click', 'h4', function () {
                self.$el.toggleClass('oe_opened');
                if (self.$el.hasClass('oe_opened')) {
                    $(".oe_searchview_custom_group_by form").show();
                } else {
                    $(".oe_searchview_custom_group_by form").hide();
                }
            }).on('click', 'button.oe_add_custom_group_by', function () {
                self.selected_custom_group_by_field = self.$('.searchview_custom_group_by_field').val() || false;
                self.selected_custom_group_by_field_descr = self.$('.searchview_custom_group_by_field option:selected').text().trim() || false;
                self.commit_search();
            }).on('submit', 'form', function (e) {
                e.preventDefault();
                self.commit_search();
            });
        return $.when(
            this._super(),
            new instance.web.Model(this.view.model).call('fields_get', {
                    context: this.view.dataset.context
                }).done(function(data) {
                    data = _.sortBy(_.pairs(data), function (f){ return f[1].string || 'zzz'; });
                    //self.group_fields = [{ string: 'ID', name: 'id', type: 'integer', searchable: true }];
                    _.each(data, function(f) {
                        var field_name = f[0];
                        var field_def = f[1];
                        if (field_def.store == true && field_def.type!='many2many' && field_def.type!='one2many' && field_name != 'id') {
                            field_def['name']=field_name;
                            self.group_fields.push( field_def );
                        }
                    });
        })).done(function () {
            self.$el.html(QWeb.render("SearchView.custom_group_by", { widget : self }))
            self.$('.oe_searchview_advanced').after(self.$el);
        });
    },
    commit_search: function () {

        if (this.selected_custom_group_by_field) {

            var context={group_by: this.selected_custom_group_by_field},
                label=_t(this.selected_custom_group_by_field_descr) || this.selected_custom_group_by_field_descr;

            this.view.query.add({
                icon: 'w',
                values: [{label: label, value: this }],
                category: _t("GroupBy"),
                field: {
                    get_context: function () {
                        return context;
                    },
                    get_domain: function () {
                    },
                    get_groupby: function () {
                        return [context];
                    }
                }
            });
        }

    }

});

instance.web.search.SearchViewDrawerCustomGroupBy = instance.web.SearchViewDrawer.include( {

    add_common_inputs: function() {

        this._super();


        // Added here to keep order in presentation
        (new instance.web.search.CustomGroupBy(this));


    }

});


};

