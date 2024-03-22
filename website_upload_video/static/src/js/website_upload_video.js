odoo.define('website_upload_video.upload_video', function (require) {
    'use strict';
    
    var web_widget = require('web_editor.widget');
    var core = require('web.core');
    // var rpc = require('web.rpc');
    
    var _t = core._t;
    
    web_widget.VideoDialog.include({
        xmlDependencies: [
            '/web_editor/static/src/xml/editor.xml',
            '/website_upload_video/static/src/xml/website_upload_video.xml'
        ],

        init: function (parent, media) {
            this._super(parent, media);
            this.media_type = 'video';
        },

        events: _.extend({}, web_widget.VideoDialog.prototype.events, {
            'click .o_website_upload_video_btn': 'upload_from_computer',
            'click .o_website_upload_audio_btn': 'upload_from_computer',
            
            'change input[type=file]': 'video_selected'
        }),
        
        upload_from_computer: function(e){
            e.preventDefault();
            var filepicker = this.$el.find('input[type=file]');
            var $target = $(e.target);
            
            if ($target.hasClass('o_website_upload_audio_btn') == true) {
                this.media_type = 'audio';
                filepicker.attr('accept', 'audio/*');
            }
            else if ($target.hasClass('o_website_upload_video_btn') == true) {
                this.media_type = 'video';
                filepicker.attr('accept', 'video/*');
            }

            if (!_.isEmpty(filepicker)){
                filepicker[0].click();
            }
            this.hideMessage();
            return false;
        },

        video_selected: function(e) {
            var self = this;
            var $input = $(e.target);
            var $form = $input.parent();
            self.toggleButton();
            window['video_upload_callback'] = function(id) {
                self.set('attachment_id', id);
                delete window['video_upload_callback'];
                self.toggleButton();
                self.showMessage();
            }
            $form.submit();
        },

        showMessage: function() {
            var span = this.$el.find('.o_website_upload_success');
            span.removeClass('hidden');
            span.addClass('show');
        },
        
        hideMessage: function() {
            var span = this.$el.find('.o_website_upload_success');
            span.removeClass('show');
            span.addClass('hidden');
        },
        
        toggleButton: function() {
            var btn = this.$el.find('.o_website_upload_video_btn');
            if(btn.hasClass('disabled')) {
                btn.removeClass('disabled').html(_t('Upload a video from your computer'));
            } else {
                btn.addClass('disabled', 'disabled').html(_t('Uploading...'));
            }
        },

        save: function() {
            this._super();

            if(this.get('attachment_id') != null) {
                // http://localhost:8070/web/content/431?access_token=cc54a78a-ec27-461d-88ae-06dad158c585&unique=dbcc93d5e16765d446514809dfa7c0314e7a10f3
                
                // var parser = new DOMParser();
                // var html_output = parser.parseFromString(
                //     "<video src='http://localhost:8070/web/content/431?access_token=cc54a78a-ec27-461d-88ae-06dad158c585&unique=dbcc93d5e16765d446514809dfa7c0314e7a10f3' controls/>",
                //     "text/html");
                var media_src = '/web/content/' + this.get('attachment_id');
                if (this.media_type == 'video') {
                    var $video = $(
                        // '<div class="media_iframe_video" date-oe-test data-oe-expression="'+ video_src +'">'+
                        //     '<div class="css_editable_mode_display">&nbsp;</div>'+
                        //     '<div class="media_iframe_video_size" contenteditable="false">&nbsp;</div>'+
                        //     '<iframe class="o_video_dialog_iframe" src="' + video_src + '"frameborder="0"></iframe>'+
                        //     // '<video class="o_video_dialog_iframe" src="http://localhost:8070/web/content/431?access_token=cc54a78a-ec27-461d-88ae-06dad158c585&unique=dbcc93d5e16765d446514809dfa7c0314e7a10f3" controls/>'
                        //     // +
                        //     // '<iframe src="' + this.$content.attr('src') + '" frameborder="0" contenteditable="false"></iframe>'+
                        // '</div>'
                        '<video style="background-color: #1a1a1a; width: 100%; height: 720px;" controls="controls" preload>' +
                        '<source src="' + media_src + '" type="video/webm" /> </video>'
                    );
                }
                
                if (this.media_type == 'audio') {
                     var $video = $(
                        '<audio style="background-color: #1a1a1a; width: 100%;" controls="controls" preload>' + 
                        '<source src="' + media_src + '" type="audio/mpeg" /> </audio>' 
                    );
                }

                $(this.media).replaceWith($video);
                this.media = $video[0];
                // return this.media;
            }// End of if
        }//end of save function
    });//End of videoDialog
}); // End of odoo define
