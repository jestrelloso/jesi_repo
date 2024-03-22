odoo.define('flyt_school_lessons.FieldVideo', function(require) {
    "use strict";
    
    var basic_fields = require('web.basic_fields');
    var FieldRegister = require('web.field_registry');
    
    var FieldVideo = basic_fields.FieldInteger.extend({
        template: 'aboutme_video',
        
        start: function() {
            this._super();
            
            if (this.value != 0 ){
                this.$el.attr('src', '/web/content/'+this.value);
            }
            else {
                this.$el.attr('class', 'o_hidden');
            }
        }
   });

    FieldRegister
        .add('video', FieldVideo);
});
