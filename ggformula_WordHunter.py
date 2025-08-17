# Function to create the PDF content
def create_pdf_content(words):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=0.5 * inch, rightMargin=0.5 * inch, topMargin=0.5 * inch, bottomMargin=0.5 * inch)
    
    styles = getSampleStyleSheet()
    
    # Using default fonts to avoid file not found errors
    penmanship_style = ParagraphStyle('Penmanship', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=24, leading=28, textColor=black, alignment=TA_CENTER)
    
    # We will create a style for the dotted words, but ReportLab doesn't support
    # opacity directly on text, so we'll use a different font or color.
    # For this example, we'll use a slightly different style to represent 'opacity'.
    dotted_style = ParagraphStyle('Dotted', parent=styles['Normal'], fontName='Courier', fontSize=24, leading=28, textColor=darkgrey, alignment=TA_CENTER)
    normal_style = ParagraphStyle('Normal', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=24, leading=28, textColor=darkgrey, alignment=TA_CENTER)
    
    story = []
    
    # Add Name and Date placeholder
    story.append(Paragraph("<b>Name:</b> ____________________ &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; <b>Date:</b> ____________________", styles['Normal']))
    story.append(Spacer(1, 0.5 * inch))
    
    story.append(Paragraph("<b> G.GEORGE - BRAIN-CHILD DICTIONARY</b>", styles['Title']))
    story.append(Spacer(1, 0.5 * inch))
    
    words_per_page = 15
    words_to_process = words[:words_per_page * 10]
    
    for i in range(0, len(words_to_process), words_per_page):
        if i > 0:
            story.append(PageBreak())
        
        page_words = words_to_process[i:i + words_per_page]
                
        # Create a table for each page with 4 columns and 5 rows
        table_data = [['' for _ in range(4)] for _ in range(5)]
        
        for j, word in enumerate(page_words):
            col_index = j % 4
            row_index = j // 4
            
            cell_content = []
            cell_content.append(Paragraph(f"<b>{word}</b>", penmanship_style))
            for _ in range(4):
                cell_content.append(Paragraph(word, normal_style))
                
            table_data[row_index][col_index] = cell_content
        
        table_style = [
            ('INNERGRID', (0,0), (-1,-1), 0.25, black),
            ('BOX', (0,0), (-1,-1), 0.25, black),
            ('TOPPADDING', (0,0), (-1,-1), 10),
            ('BOTTOMPADDING', (0,0), (-1,-1), 10),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ]

        story.append(Table(table_data, colWidths=[2*inch]*4, style=table_style))
        story.append(Spacer(1, 0.5 * inch))

    # Footer
    story.append(Spacer(1, 0.5 * inch))
    story.append(Paragraph("Created with G.GEORGE - BRAIN-CHILD DICTIONARY", styles['Normal']))

    doc.build(story)
    return buffer.getvalue()
