odoo.define('flyt_school_lesson.UserMenu', function (require) {
    "use strict";
    
    var UserMenu = require('web.UserMenu');

    var menu = UserMenu.include({
        _onMenuDocumentation: function () {
            window.open('https://flyt.online/', '_blank');
        },
        _onMenuSupport: function () {
            window.open('https://flyt.online/', '_blank');
        },
    });
    
    return menu;
});
