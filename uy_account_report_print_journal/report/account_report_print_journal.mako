## -*- coding: utf-8 -*-
<!DOCTYPE html SYSTEM "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
    <head>
        <style type="text/css">
            .overflow_ellipsis {
                text-overflow: ellipsis;
                overflow: hidden;
                white-space: nowrap;
            }
            ${css}
        </style>
    </head>
    <body>
        <%!
        def amount(text):
            return text.replace('-', '&#8209;')  # replace by a non-breaking hyphen (it will not word-wrap between hyphen and numbers)
        %>

        <%setLang(user.lang)%>

        <div class="act_as_table data_table">
            <div class="act_as_row labels">
                <div class="act_as_cell">${_('Chart of Account')}</div>
                <div class="act_as_cell">${_('Fiscal Year')}</div>
                <div class="act_as_cell">
                    %if filter_form(data) == 'filter_date':
                        ${_('Dates Filter')}
                    %else:
                        ${_('Periods Filter')}
                    %endif
                </div>
                <div class="act_as_cell">${_('Journal Filter')}</div>
                <div class="act_as_cell">${_('Target Moves')}</div>
            </div>
            <div class="act_as_row">
                <div class="act_as_cell">${ chart_account.name }</div>
                <div class="act_as_cell">${ fiscalyear.name if fiscalyear else '-' }</div>
                <div class="act_as_cell">
                    ${_('From:')}
                    %if filter_form(data) == 'filter_date':
                        ${formatLang(start_date, date=True) if start_date else u'' }
                    %else:
                        ${start_period.name if start_period else u''}
                    %endif
                    ${_('To:')}
                    %if filter_form(data) == 'filter_date':
                        ${ formatLang(stop_date, date=True) if stop_date else u'' }
                    %else:
                        ${stop_period.name if stop_period else u'' }
                    %endif
                </div>
                <div class="act_as_cell">
                    %if journals(data):
                        ${', '.join([journal.name for journal in journals(data)])}
                    %else:
                        ${_('All')}
                    %endif

                </div>
                <div class="act_as_cell">${ display_target_move(data) }</div>
            </div>
        </div>

        %for row in objects:
          %if moves.get(row.id, False):
            <%
            account_total_debit = 0.0
            account_total_credit = 0.0
            account_total_currency = 0.0
            %>

            %if gb_journal_period:
                <div class="account_title bg" style="width: 1080px; margin-top: 20px; font-size: 12px;">${row.journal_id.name} - ${row.period_id.name}</div>
            %elif gb_period:
                <div class="account_title bg" style="width: 1080px; margin-top: 20px; font-size: 12px;">${row.name}</div>
            %else:
                <div class="account_title bg" style="width: 1080px; margin-top: 20px; font-size: 12px;"></div>
            %endif

            <!-- we use div with css instead of table for tabular data because div do not cut rows at half at page breaks -->
            <div class="act_as_table list_table" style="margin-top: 5px;">
                <div class="act_as_thead">
                    <div class="act_as_row labels">
                        %if not gb_journal_period:
                            ## journal
                            <div class="act_as_cell">${_('Journal')}</div>
                            %if not gb_period:
                                ## period
                                <div class="act_as_cell">${_('Period')}</div>
                            %endif
                        %endif
                        ## date
                        <div class="act_as_cell first_column">${_('Date')}</div>
                        ## move
                        <div class="act_as_cell">${_('Entry')}</div>
                        ## account code
                        <div class="act_as_cell">${_('Account')}</div>
                        ## date
                        <div class="act_as_cell">${_('Due Date')}</div>
                        ## partner
                        <div class="act_as_cell" style="width: 170px;">${_('Partner')}</div>
                        ## label
                        <div class="act_as_cell" style="width: 200px;">${_('Label')}</div>
                        ## reference
                        <div class="act_as_cell" style="width: 150px;">${_('Reference')}</div>
                        ## debit
                        <div class="act_as_cell amount">${_('Debit')}</div>
                        ## credit
                        <div class="act_as_cell amount">${_('Credit')}</div>
                        %if amount_currency(data):
                            ## currency balance
                            <div class="act_as_cell amount sep_left">${_('Curr. Balance')}</div>
                            ## curency code
                            <div class="act_as_cell amount" style="text-align: right;">${_('Curr.')}</div>
                        %endif
                    </div>
                </div>
                %for move in moves.get(row.id, []):
                <%
                new_move = True
                %>
                    %for line in move.line_id:
                    <div class="act_as_tbody">
                        <%
                        account_total_debit += line.debit or 0.0
                        account_total_credit += line.credit or 0.0
                        %>
                        <div class="act_as_row lines">
                            %if not gb_journal_period:
                                ## journal
                                <div class="act_as_cell">${line.journal_id.name}</div>
                                %if not gb_period:
                                    ## period
                                    <div class="act_as_cell">${line.period_id.name}</div>
                                %endif
                            %endif
                            ## date
                            <div class="act_as_cell first_column">${formatLang(move.date, date=True) if new_move else ''}</div>
                            ## move
                            <div class="act_as_cell">${(move.name) if new_move else ''}</div>
                            ## account code
                            <div class="act_as_cell">${line.account_id.code}</div>
                            ## date
                            <div class="act_as_cell">${formatLang(line.date_maturity or '', date=True)}</div>
                            ## partner
                            <div class="act_as_cell overflow_ellipsis" style="width: 170px;">${line.partner_id.name if (new_move and line.partner_id) else ''}</div>
                            ## label
                            <div class="act_as_cell overflow_ellipsis" style="width: 200px;">${line.name}</div>
                            ## reference
                            <div class="act_as_cell" style="width: 150px;">${get_line_reference(line)}</div>
                            ## debit
                            <div class="act_as_cell amount">${formatLang(line.debit) if line.debit else ''}</div>
                            ## credit
                            <div class="act_as_cell amount">${formatLang(line.credit) if line.credit else ''}</div>
                            %if amount_currency(data):
                                ## currency balance
                                <div class="act_as_cell amount sep_left">${formatLang(line.amount_currency) if line.amount_currency else ''}</div>
                                ## curency code
                                <div class="act_as_cell amount" style="text-align: right;">${line.currency_id.symbol or ''}</div>
                            %endif
                        </div>
                        <%
                        new_move = False
                        %>
                    </div>
                    %endfor
                %endfor
                <div class="act_as_row lines labels">
                    %if not gb_journal_period:
                        ## journal
                        <div class="act_as_cell first_column"></div>
                        %if not gb_period:
                            ## period
                            <div class="act_as_cell"></div>
                        %endif
                    %endif
                    ## date
                    <div class="act_as_cell first_column"></div>
                    ## move
                    <div class="act_as_cell"></div>
                    ## account code
                    <div class="act_as_cell"></div>
                    ## date
                    <div class="act_as_cell"></div>
                    ## partner
                    <div class="act_as_cell" style="width: 170px;"></div>
                    ## label
                    <div class="act_as_cell" style="width: 200px;"></div>
                    ## reference
                    <div class="act_as_cell" style="width: 150px;"></div>
                    ## debit
                    <div class="act_as_cell amount">${formatLang(account_total_debit) | amount }</div>
                    ## credit
                    <div class="act_as_cell amount">${formatLang(account_total_credit) | amount }</div>
                    %if amount_currency(data):
                      ## currency balance
                      <div class="act_as_cell amount sep_left"></div>
                      ## currency code
                      <div class="act_as_cell" style="text-align: right; right;"></div>
                    %endif
                </div>
            </div>
          %endif
        %endfor
    </body>
</html>
