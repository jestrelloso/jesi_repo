var isReactionVideo = false
var videoQuestionView = null
var recordingTimeLimit = 0
var mediaRecorder = null
var recordedBlobs = null
var isRecording = false
var oneSecond = 1000
var currentTime = 0
var endTime = 0
var videoView = null
var audioView = null
var messageView = null
var isPaused = false
var prefix = ''
var mode = ''
var audioRecordingConstraints = {
    audio: true
}

var videoRecordingConstraints = {
    audio: true,
    video: true
}

// On document ready
$(document).ready(() => {
    // For `evaluation_templates` audio and video answer views
    $("[media-tag='media-answer-view']").each((i, el) => {
        addMediaViewEventListener(el)
    })

    // Audio recording record and pause buttons
    $("input[id^='audio-recording-']").each((i, el) => {
        $(el).click(() => {
            mode = 'audio'
            prefix = $(el).attr('prefix')
            audioView = document.querySelector('#preview-audio-recording-' + prefix)
            messageView = $('#message-' + mode + '-recording-' + prefix)
            isRecording = !isRecording
            toggleOtherRecordingButtons(el, isRecording)
            togglePauseButton(!isRecording)
            toggleRecordingIndicator(!isRecording)

            if (isRecording) { // Start audio recording
                startRecording(el)
            } else { // Stop audio recording + save
                clickResumeRecording()
                stopRecording(el)
            }

            audioView.onvolumechange = (() => {
                if (audioView.muted == false){
                    alert('Please mute the volume while recording to avoid unnecessary feedback')
                }
                audioView.muted = true
            })
        })
    })

    $("input[id^='pause-audio-recording-']").each((i, el) => {
        $(el).click(() => {
            mode = 'audio'
            prefix = $(el).attr('prefix')
            isPaused = !isPaused
            toggleRecordingIndicator(isPaused)

            if (isPaused) { // Pause audio recording
                pauseRecording(el)
            } else { // Resume audio recording
                resumeRecording(el)
            }
        })
    })

    // Video recording record and pause buttons
    $("input[id^='video-recording-']").each((i, el) => {
        $(el).click(() => {
            mode = 'video'
            prefix = $(el).attr('prefix')
            videoView = document.querySelector('#preview-video-recording-' + prefix)
            messageView = $('#message-' + mode + '-recording-' + prefix)
            isRecording = !isRecording
            toggleOtherRecordingButtons(el, isRecording)
            togglePauseButton(!isRecording)
            toggleRecordingIndicator(!isRecording)

            if (isRecording) { // Start video recording
                startRecording(el)
            } else { // Stop video recording + save
                clickResumeRecording()
                stopRecording(el)
            }

            videoView.onvolumechange = (() => {
                if (videoView.muted == false){
                    alert('Please mute the volume while recording to avoid unnecessary feedback')
                }
                videoView.muted = true
            })
        })

    })

    $("input[id^='pause-video-recording-']").each((i, el) => {
        $(el).click(() => {
            mode = 'video'
            prefix = $(el).attr('prefix')
            isPaused = !isPaused
            toggleRecordingIndicator(isPaused)

            if (isPaused) { // Pause video recording
                pauseRecording(el)
            } else { // Resume video recording
                resumeRecording(el)
            }
        })
    })

    $("video[is-reaction-video='True']").each((i, el) => {
        attachVideoOverlayStatusChecker(el)
    })

    // Attach blur listener / `on window out of focus listener` to pause current recording
    $(window).blur(() => {
        if (isRecording && !isPaused && mediaRecorder != null) {
            $("input[id^='pause-" + mode + "-recording-" + prefix + "']").click()
        }
    })
})

startRecording = (recordButton) => {
    messageView.removeClass('text-danger')
    recordingTimeLimit = parseInt($("input[name='" + prefix + "']").attr('time-limit'))
    
    $("input[name="+prefix+"]").attr('value', 'Recording')
    
    setDisplayMessage("Recording...")
    countdownRecord(recordingTimeLimit)
    $(recordButton).val("Stop")
    if (mode == 'audio') {
        captureUserMedia(audioRecordingConstraints, onMediaSuccess, onMediaError)
    } else if (mode == 'video') {
        isReactionVideo = Boolean($("input[name='" + prefix + "']").attr('is-reaction-video'))
        if (isReactionVideo) {
            videoQuestionView = document.querySelector('#video-question-' + prefix)
            toggleVideoQuestionViews(false)
            videoQuestionView.play()
        }
        captureUserMedia(videoRecordingConstraints, onMediaSuccess, onMediaError)
    }
}

pauseRecording = (pauseButton) => {
    mediaRecorder.pause()
    $(pauseButton).val("Resume")
    if (recordingTimeLimit > 0) {
        ({ minutes, seconds } = getMinutesAndSeconds())
        setDisplayMessage("Recording paused. Time left: " + minutes + "m " + seconds + "s")
    } else {
        setDisplayMessage("Recording paused.")
    }
    if (mode == 'video' && isReactionVideo) {
        videoQuestionView.pause()
    }
}

resumeRecording = (resumeButton) => {
    setDisplayMessage("Recording...")
    $(resumeButton).val("Pause")
    mediaRecorder.resume()
    if (mode == 'video' && isReactionVideo) {
        videoQuestionView.play()
    }
}

clickResumeRecording = () => {
    if (isPaused) {
        $("#pause-" + mode + "-recording-" + prefix).click()
    }
}

stopRecording = (stopButton) => {
    $(stopButton).val("Record")
    currentTime = endTime
    mediaRecorder.stop()
    window.stream.getTracks().forEach((track) => {
        track.stop()
    })

    addMediaViewEventListener(mode == 'video' ? videoView : audioView)
    toggleRecordingIndicator(!isRecording && !isPaused)
    loadRecording()
    if (mode == 'video' && isReactionVideo) {
        toggleVideoQuestionViews(true)
        videoQuestionView.pause()
    }
}

toggleVideoQuestionViews = (done) => {
    $('#preview-video-recording-' + prefix).prop('hidden', !done)
    $('#video-question-' + prefix).prop('hidden', done)
}

toggleRecordingIndicator = (hidden) => {
    $('#blinker-' + prefix).prop('hidden', hidden)
}

toggleOtherRecordingButtons = (active, disabled) => {
    $("input[id^='audio-recording-']").each((i, el) => {
        if (!$(el).is($(active))) {
            $(el).prop('disabled', disabled)
        }
    })

    $("input[id^='video-recording-']").each((i, el) => {
        if (!$(el).is($(active))) {
            $(el).prop('disabled', disabled)
        }
    })
}

togglePauseButton = (hidden) => {
    $('#pause-' + mode + '-recording-' + prefix).prop('hidden', hidden)
}

setDisplayMessage = (message) => {
    messageView.text(message)
}

// Recording proper
captureUserMedia = (mediaConstraints, onMediaSuccess, onMediaError) => {
    recordedBlobs = []
    navigator.mediaDevices.getUserMedia(mediaConstraints).then(onMediaSuccess).catch(onMediaError)
}

onMediaSuccess = (stream) => {
    window.stream = stream
    var options = { mimeType: 'video/webm;codecs=vp9' }
    if (!MediaRecorder.isTypeSupported(options.mimeType)) {
        options = { mimeType: 'video/webm;codecs=vp8' }
        if (!MediaRecorder.isTypeSupported(options.mimeType)) {
            options = { mimeType: 'video/webm' }
            if (!MediaRecorder.isTypeSupported(options.mimeType)) {
                options = { mimeType: '' }
            }
        }
    }

    try {
        mediaRecorder = new MediaRecorder(window.stream, options)
    } catch (e) {
        // console.error('Exception while creating MediaRecorder: ' + e)
        alert('Exception while creating MediaRecorder: '
            + e + '. mimeType: ' + options.mimeType + '. Please allow Jesi '
            + 'to access your microphone and camera.')
        return
    }

    if (mode == 'video') {
        videoView.srcObject = window.stream
    }

    mediaRecorder.ondataavailable = handleDataAvailable
    mediaRecorder.start(10)
}

onMediaError = (e) => {
    // console.error('flyt_school_lessons media_error', e)
}

handleDataAvailable = (event) => {
    if (event.data && event.data.size > 0) {
        recordedBlobs.push(event.data)
    }
}

loadRecording = () => {
    if (mode == 'audio') {
        $('#preview-audio-recording-' + prefix).attr('hidden', false)
    } else if (mode == 'video') {
        videoView.srcObject = null
    }

    let buffer = new Blob(recordedBlobs, { type: mode + '/webm' })
    blobToFile(buffer, ajaxPostRecordedFile)
}

addMediaViewEventListener = (mediaView) => {
    mediaView.addEventListener('loadedmetadata', function () {
        if (mediaView.duration === Infinity) {
            mediaView.currentTime = 1e101
            mediaView.ontimeupdate = function () {
                mediaView.currentTime = 0.1
                mediaView.ontimeupdate = function () {
                    delete mediaView.ontimeupdate
                }
            }
        }
    })
}

// AJAX POST to '/answer_recording/file'
ajaxPostRecordedFile = (recordedFile) => {
    setDisplayMessage('Uploading ' + mode + ' response.')
    let formData = new FormData()
    formData.append('csrf_token', odoo.csrf_token)
    formData.append('recordedFile', recordedFile)
    formData.append('prefix', prefix)
    formData.append('mimeType', mode + '/webm')
    $.ajax({
        url: '/answer_recording/file',
        type: 'post',
        processData: false,
        contentType: false,
        data: formData,
        success: onAjaxPostSuccess,
        error: onAjaxPostError
    })
}

onAjaxPostSuccess = (data, textStatus, jqXHR) => {
    setDisplayMessage(mode.charAt(0).toLocaleUpperCase() + mode.substr(1) + ' response recorded.')
    let response = JSON.parse(data)

    // console.debug('AJAX POST success... ' + response.message)
    // console.debug('srcPath: ' + response.srcPath)

    if (mode == 'audio') {
        audioView.src = response.srcPath
        audioView.onvolumechange = null
    } else if (mode == 'video') {
        videoView.src = response.srcPath
        videoView.onvolumechange = null
    }
    $("input[name="+prefix+"]").attr('value', 'Done Recording')
}

onAjaxPostError = (error) => {
    setDisplayMessage(mode.charAt(0).toLocaleUpperCase() + mode.substr(1) + ' response upload failed. Please try again.')
    // console.debug('AJAX POST failed... ' + error)
}

blobToFile = (blob, callback) => {
    let recordedFile = new File([blob], prefix)
    callback(recordedFile)
}

countdownRecord = (minutes) => {
    if (minutes > 0) {
        currentTime = (new Date()).getTime()
        endTime = (new Date()).getTime() + (minutes * oneSecond * 60)
        updateMessage()
    }
}

updateMessage = () => {
    if (currentTime + oneSecond < endTime) {
        setTimeout(updateMessage, oneSecond)
    }

    if (isRecording && !isPaused) {
        currentTime += oneSecond
        if (currentTime >= endTime) {
            $("#" + mode + "-recording-" + prefix).click()
            setDisplayMessage("Recording time is up, you can play your recorded response.")
        } else {
            ({ minutes, seconds } = getMinutesAndSeconds())
            setDisplayMessage("Recording... Time left: " + minutes + "m " + seconds + "s")
            if (minutes == 0 && seconds <= 30) {
                messageView.addClass('text-danger')
            }
        }
    } else {
        messageView.removeClass('text-danger')
    }
}

getMinutesAndSeconds = () => {
    time = new Date()
    time.setTime(endTime - currentTime)
    return {
        minutes: time.getMinutes(),
        seconds: time.getSeconds()
    }
}

// Overlay checker for reaction videos
attachVideoOverlayStatusChecker = (reactionVideoView) => {
    attachmentId = $(reactionVideoView).attr('attached-media')
    reactionVideoMessageView = $('#video-attachment-' + attachmentId)
    reactionVideoQuestionView = $("div[video-question-id='" + $(reactionVideoView).attr('video-question-id') + "']")
    checkVideoOverlayStatus(attachmentId, reactionVideoMessageView, reactionVideoQuestionView)
}

checkVideoOverlayStatus = (attachmentId, reactionVideoMessageView, reactionVideoQuestionView) => {
    // console.debug('Checking overlay status of attachment ' + attachmentId + '...')
    setTimeout(() => {
        $.ajax({
            url: '/video_overlay_status/' + attachmentId,
            type: 'get',
            processData: false,
            contentType: false,
            success: onAjaxGetVideoOverlayStatusSuccess,
            error: onAjaxGetVideoOverlayStatusError
        })
    }, 1000)
}

onAjaxGetVideoOverlayStatusSuccess = (data, textStatus, jqXHR) => {
    let response = JSON.parse(data)
    attachmentStatus = response.attachmentStatus
    // console.debug('Attachment ' + attachmentId + ' ' + attachmentStatus + '...')
    reactionVideoView = $("video[attached-media='" + attachmentId + "']")
    if (attachmentStatus == 'attached') {
        reactionVideoMessageView.remove()
        reactionVideoQuestionView.remove()
        reactionVideoView[0].firstElementChild.src = '/web/content/' + attachmentId
        reactionVideoView[0].load()
    } else {
        reactionVideoMessageView.prop('hidden', false)
        checkVideoOverlayStatus(attachmentId, reactionVideoMessageView, reactionVideoQuestionView)
    }
}

onAjaxGetVideoOverlayStatusError = (error) => {
    // console.error('Error checking video overlay status of attachment ' + attachmentId + '. Trying again...')
    checkVideoOverlayStatus(attachmentId, reactionVideoMessageView, reactionVideoQuestionView)
}
