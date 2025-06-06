def emit_to_side_output(ctx, tag, data):
    """Helper function to handle different context types"""
    try:
        if hasattr(ctx, 'output'):
            ctx.output(tag, data)
        else:
            from pyflink.datastream.functions import RuntimeContext
            if isinstance(ctx, RuntimeContext):
                ctx.get_side_output(tag).collect(data)
            else:
                print(f"Warning: Could not emit to side output. Context type: {type(ctx)}")
    except Exception as e:
        print(f"Error emitting to side output: {str(e)}")