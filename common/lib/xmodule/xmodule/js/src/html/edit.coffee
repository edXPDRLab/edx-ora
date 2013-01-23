class @HTMLEditingDescriptor
  @isInactiveClass : "is-inactive"

  constructor: (element) ->
    @element = element;

    @advanced_editor = CodeMirror.fromTextArea($(".edit-box", @element)[0], {
      mode: "text/html"
      lineNumbers: true
      lineWrapping: true
    })

    $(@advanced_editor.getWrapperElement()).addClass(HTMLEditingDescriptor.isInactiveClass)

#   This is a workaround for the fact that tinyMCE's baseURL property is not getting correctly set on AWS
#   instances (like sandbox). It is not necessary to explicitly set baseURL when running locally.
    tinyMCE.baseURL = '/static/js/vendor/tiny_mce'
    @tiny_mce_textarea = $(".tiny-mce", @element).tinymce({
      script_url : '/static/js/vendor/tiny_mce/tiny_mce.js',
      theme : "advanced",
      skin: 'studio',
      schema: "html5",
      # TODO: we should share this CSS with studio (and LMS)
      content_css : "/static/css/tiny-mce.css",
      # We may want to add "styleselect" when we collect all styles used throughout the LMS
      theme_advanced_buttons1 : "formatselect,bold,italic,underline,bullist,numlist,outdent,indent,blockquote,link,unlink",
      theme_advanced_toolbar_location : "top",
      theme_advanced_toolbar_align : "left",
      theme_advanced_statusbar_location : "none",
      theme_advanced_resizing : true,
      theme_advanced_blockformats : "p,code,h2,h3,blockquote",
      width: '100%',
      height: '400px',
      # Cannot get access to tinyMCE Editor instance (for focusing) until after it is rendered.
      # The tinyMCE callback passes in the editor as a paramter.
      init_instance_callback: @focusVisualEditor
    })

    @showingVisualEditor = true
    @element.on('click', '.editor-tabs .tab', @onSwitchEditor)

  onSwitchEditor: (e)=>
    e.preventDefault();

    if not $(e.currentTarget).hasClass('current')
      $('.editor-tabs .current').removeClass('current')
      $(e.currentTarget).addClass('current')
      $('table.mceToolbar').toggleClass(HTMLEditingDescriptor.isInactiveClass)
      $(@advanced_editor.getWrapperElement()).toggleClass(HTMLEditingDescriptor.isInactiveClass)

      visualEditor = @getVisualEditor()
      if $(e.currentTarget).attr('data-tab') is 'visual'
        @showVisualEditor(visualEditor)
      else
        @showAdvancedEditor(visualEditor)

  # Show the Advanced (codemirror) Editor. Pulled out as a helper method for unit testing.
  showAdvancedEditor: (visualEditor) ->
    if visualEditor.isDirty()
      @advanced_editor.setValue(visualEditor.getContent({no_events: 1}))
      @advanced_editor.setCursor(0)
    @advanced_editor.refresh()
    @advanced_editor.focus()
    @showingVisualEditor = false

  # Show the Visual (tinyMCE) Editor. Pulled out as a helper method for unit testing.
  showVisualEditor: (visualEditor) ->
    visualEditor.setContent(@advanced_editor.getValue())
    # In order for isDirty() to return true ONLY if edits have been made after setting the text,
    # both the startContent must be sync'ed up and the dirty flag set to false.
    visualEditor.startContent = visualEditor.getContent({format: "raw", no_events: 1});
    visualEditor.isNotDirty = true
    @focusVisualEditor(visualEditor)
    @showingVisualEditor = true

  focusVisualEditor: (visualEditor) ->
    visualEditor.focus()

  getVisualEditor: ->
    ###
    Returns the instance of TinyMCE.
    This is different from the textarea that exists in the HTML template (@tiny_mce_textarea.
    ###
    return tinyMCE.get($('.tiny-mce', this.element).attr('id'))

  save: ->
    @element.off('click', '.editor-tabs .tab', @onSwitchEditor)
    text = @advanced_editor.getValue()
    visualEditor = @getVisualEditor()
    if @showingVisualEditor and visualEditor.isDirty()
      text = visualEditor.getContent({no_events: 1})
    data: text