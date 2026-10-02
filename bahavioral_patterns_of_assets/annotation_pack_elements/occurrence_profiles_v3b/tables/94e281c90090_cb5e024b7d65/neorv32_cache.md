# Occurrence profiles: neorv32_cache

rulebook `c44db45cd3ed` · classify `94e281c90090` · validate `cb5e024b7d65` · model `gpt-5-mini` · effort `medium`

Count: Context and Path from the structure step for 427 of 427 entries.

Context and Path: read off the source by code (the structure step, tree-sitter grammar); the Role and the SITE tags are the model's.

## Entity neorv32_cache

### clk_i

from validate

| Occurrence Lines | Context | Path | SITE Tagged |
| --- | --- | --- | --- |
| line 35 | port clause 34-41 in entity 27-42; Declared as a port in the entity's port clause. | - | DECL_PORT |
| line 114 | process ctrl_engine_sync 114-128 in architecture 44-294; Named in the sensitivity list of the process ctrl_engine_sync (process header). | - | PROCESS_TRIG |
| line 125 | elsif branch 125-126 in if 116-127 in process ctrl_engine_sync 114-128 in architecture 44-294; Argument of rising_edge(...) in the elsif condition of the if statement inside process ctrl_engine_sync. | not (rstn_i = '0') | EDGE_CHECK |
| line 281 | port map 278-292 in instance neorv32_cache_memory_inst 273-292 in architecture 44-294; Actual in a port map association, associated with the formal clk_i of the instantiated unit. | - | ASSOC_ACTUAL |

### rstn_i

from validate

| Occurrence Lines | Context | Path | SITE Tagged |
| --- | --- | --- | --- |
| line 36 | port clause 34-41 in entity 27-42; Declared as a port in the entity's port clause. | - | DECL_PORT |
| line 114 | process ctrl_engine_sync 114-128 in architecture 44-294; Named in the sensitivity list of the process ctrl_engine_sync (process header). | - | PROCESS_TRIG |
| line 116 | then branch 116-124 in if 116-127 in process ctrl_engine_sync 114-128 in architecture 44-294; In the condition of an if statement (if rstn_i = '0') inside process ctrl_engine_sync. | - | IF_COND |
| line 280 | port map 278-292 in instance neorv32_cache_memory_inst 273-292 in architecture 44-294; Actual in a port map association, associated with the formal rstn_i of the instantiated unit. | - | ASSOC_ACTUAL |

### host_req_i

from validate

| Occurrence Lines | Context | Path | SITE Tagged |
| --- | --- | --- | --- |
| line 37 | port clause 34-41 in entity 27-42; Declared as a port in the entity's port clause. | - | DECL_PORT |
| line 133 | process ctrl_engine_comb 133-268 in architecture 44-294; Named in the sensitivity list of the process ctrl_engine_comb (process header). | - | PROCESS_TRIG |
| line 137 | process ctrl_engine_comb 133-268 in architecture 44-294; Record base; field reached: stb. | - | FIELD_USE |
| line 138 | process ctrl_engine_comb 133-268 in architecture 44-294; Record base; field reached: fence. | - | FIELD_USE |
| line 149 | process ctrl_engine_comb 133-268 in architecture 44-294; Record base; field reached: addr. | - | FIELD_USE |
| line 151 | process ctrl_engine_comb 133-268 in architecture 44-294; Record base; field reached: data. | - | FIELD_USE |
| line 159 | process ctrl_engine_comb 133-268 in architecture 44-294; Whole right-hand side of a sequential signal assignment (the entire RHS is the record host_req_i). | - | DIRR_ASS |
| line 168 | then branch 168-169 in if 168-176 in case alternative S_IDLE 166-176 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Record base; field reached: fence. | ctrl.state = S_IDLE | FIELD_USE |
| line 170 | elsif branch 170-175 in if 168-176 in case alternative S_IDLE 166-176 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Record base; field reached: stb. | ctrl.state = S_IDLE AND not ((host_req_i.fence = '1') or (ctrl.buf_sync = '1')) | FIELD_USE |
| line 171 | then branch 171-173 in if 171-174 in elsif branch 170-175 in if 168-176 in case alternative S_IDLE 166-176 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Record base; field reached: addr. | ctrl.state = S_IDLE AND not ((host_req_i.fence = '1') or (ctrl.buf_sync = '1')) AND (host_req_i.stb = '1') or (ctrl.buf_req = '1') | FIELD_USE |
| line 172 | then branch 171-173 in if 171-174 in elsif branch 170-175 in if 168-176 in case alternative S_IDLE 166-176 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Record base; field reached: amo. | ctrl.state = S_IDLE AND not ((host_req_i.fence = '1') or (ctrl.buf_sync = '1')) AND (host_req_i.stb = '1') or (ctrl.buf_req = '1') | FIELD_USE |
| line 172 | then branch 171-173 in if 171-174 in elsif branch 170-175 in if 168-176 in case alternative S_IDLE 166-176 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Record base; field reached: debug. | ctrl.state = S_IDLE AND not ((host_req_i.fence = '1') or (ctrl.buf_sync = '1')) AND (host_req_i.stb = '1') or (ctrl.buf_req = '1') | FIELD_USE |
| line 180 | case alternative S_LOOKUP 178-205 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Record base; field reached: addr. | ctrl.state = S_LOOKUP | FIELD_USE |
| line 181 | case alternative S_LOOKUP 178-205 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Record base; field reached: addr. | ctrl.state = S_LOOKUP | FIELD_USE |
| line 190 | then branch 190-192 in if 190-197 in elsif branch 189-197 in if 186-205 in case alternative S_LOOKUP 178-205 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Record base; field reached: rw. | ctrl.state = S_LOOKUP AND not (ctrl.buf_dir = '1') AND cache_i.sta_hit = '1' | FIELD_USE |
| line 194 | else branch 193-196 in if 190-197 in elsif branch 189-197 in if 186-205 in case alternative S_LOOKUP 178-205 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Record base; field reached: ben. | ctrl.state = S_LOOKUP AND not (ctrl.buf_dir = '1') AND cache_i.sta_hit = '1' AND not ((host_req_i.rw = '0') or (READ_ONLY = true)) | FIELD_USE |
| line 199 | then branch 199-200 in if 199-204 in else branch 198-204 in if 186-205 in case alternative S_LOOKUP 178-205 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Record base; field reached: rw. | ctrl.state = S_LOOKUP AND not (ctrl.buf_dir = '1') AND not (cache_i.sta_hit = '1') | FIELD_USE |

### host_req_i.addr

from validate

| Occurrence Lines | Context | Path | SITE Tagged |
| --- | --- | --- | --- |
| line 37 | port clause 34-41 in entity 27-42; Declaration of the field via the base's port declaration; the record type is declared outside this source. | - | DECL_FIELD |
| line 149 | process ctrl_engine_comb 133-268 in architecture 44-294; Whole right-hand side of a sequential signal assignment (cache_o.addr <= host_req_i.addr). | - | DIRR_ASS |
| line 171 | then branch 171-173 in if 171-174 in elsif branch 170-175 in if 168-176 in case alternative S_IDLE 166-176 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Slice (31 downto 28) of host_req_i.addr used inside the if condition (as part of unsigned(...)). | ctrl.state = S_IDLE AND not ((host_req_i.fence = '1') or (ctrl.buf_sync = '1')) AND (host_req_i.stb = '1') or (ctrl.buf_req = '1') | IF_COND, PART_SELECT |
| line 180 | case alternative S_LOOKUP 178-205 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Slice (31 downto 32-tag_size_c) of host_req_i.addr used as the entire right-hand side of a signal assignment. | ctrl.state = S_LOOKUP | PART_SELECT |
| line 181 | case alternative S_LOOKUP 178-205 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Slice ((offset_size_c+2+index_size_c)-1 downto offset_size_c+2) of host_req_i.addr used as the entire right-hand side of a signal assignment. | ctrl.state = S_LOOKUP | PART_SELECT |

### host_req_i.data

from validate

| Occurrence Lines | Context | Path | SITE Tagged |
| --- | --- | --- | --- |
| line 37 | port clause 34-41 in entity 27-42; Declaration of the field via the base's port declaration; the record type is declared outside this source. | - | DECL_FIELD |
| line 151 | process ctrl_engine_comb 133-268 in architecture 44-294; Whole right-hand side of a sequential signal assignment (cache_o.data <= host_req_i.data). | - | DIRR_ASS |

### host_req_i.ben

from validate

| Occurrence Lines | Context | Path | SITE Tagged |
| --- | --- | --- | --- |
| line 37 | port clause 34-41 in entity 27-42; Declaration of the field via the base's port declaration; the record type is declared outside this source. | - | DECL_FIELD |
| line 194 | else branch 193-196 in if 190-197 in elsif branch 189-197 in if 186-205 in case alternative S_LOOKUP 178-205 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Whole right-hand side of a sequential signal assignment (cache_o.we <= host_req_i.ben). | ctrl.state = S_LOOKUP AND not (ctrl.buf_dir = '1') AND cache_i.sta_hit = '1' AND not ((host_req_i.rw = '0') or (READ_ONLY = true)) | DIRR_ASS |

### host_req_i.stb

from validate

| Occurrence Lines | Context | Path | SITE Tagged |
| --- | --- | --- | --- |
| line 37 | port clause 34-41 in entity 27-42; Declaration of the field via the base's port declaration; the record type is declared outside this source. | - | DECL_FIELD |
| line 137 | process ctrl_engine_comb 133-268 in architecture 44-294; Operand on the right-hand side of a sequential signal assignment joined by an operator (ctrl_nxt.buf_req <= ctrl.buf_req or host_req_i.stb). | - | RHS_OPERAND |
| line 170 | elsif branch 170-175 in if 168-176 in case alternative S_IDLE 166-176 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Used in an if/elsif condition (host_req_i.stb = '1') inside a sequential if statement. | ctrl.state = S_IDLE AND not ((host_req_i.fence = '1') or (ctrl.buf_sync = '1')) | IF_COND |

### host_req_i.rw

from validate

| Occurrence Lines | Context | Path | SITE Tagged |
| --- | --- | --- | --- |
| line 37 | port clause 34-41 in entity 27-42; Declaration of the field via the base's port declaration; the record type is declared outside this source. | - | DECL_FIELD |
| line 190 | then branch 190-192 in if 190-197 in elsif branch 189-197 in if 186-205 in case alternative S_LOOKUP 178-205 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Used in an if condition (host_req_i.rw = '0') inside a sequential if statement. | ctrl.state = S_LOOKUP AND not (ctrl.buf_dir = '1') AND cache_i.sta_hit = '1' | IF_COND |
| line 199 | then branch 199-200 in if 199-204 in else branch 198-204 in if 186-205 in case alternative S_LOOKUP 178-205 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Used in an if condition (host_req_i.rw = '0') inside a sequential if statement. | ctrl.state = S_LOOKUP AND not (ctrl.buf_dir = '1') AND not (cache_i.sta_hit = '1') | IF_COND |

### host_req_i.src

from validate

| Occurrence Lines | Context | Path | SITE Tagged |
| --- | --- | --- | --- |
| line 37 | port clause 34-41 in entity 27-42; Declaration of the field via the base's port declaration; the record type is declared outside this source. | - | DECL_FIELD |

### host_req_i.priv

from validate

| Occurrence Lines | Context | Path | SITE Tagged |
| --- | --- | --- | --- |
| line 37 | port clause 34-41 in entity 27-42; Declaration of the field via the base's port declaration; the record type is declared outside this source. | - | DECL_FIELD |

### host_req_i.debug

from validate

| Occurrence Lines | Context | Path | SITE Tagged |
| --- | --- | --- | --- |
| line 37 | port clause 34-41 in entity 27-42; Declaration of the field via the base's port declaration; the record type is declared outside this source. | - | DECL_FIELD |
| line 172 | then branch 171-173 in if 171-174 in elsif branch 170-175 in if 168-176 in case alternative S_IDLE 166-176 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Used in an if condition (host_req_i.debug = '1') inside a sequential if statement. | ctrl.state = S_IDLE AND not ((host_req_i.fence = '1') or (ctrl.buf_sync = '1')) AND (host_req_i.stb = '1') or (ctrl.buf_req = '1') | IF_COND |

### host_req_i.amo

from validate

| Occurrence Lines | Context | Path | SITE Tagged |
| --- | --- | --- | --- |
| line 37 | port clause 34-41 in entity 27-42; Declaration of the field via the base's port declaration; the record type is declared outside this source. | - | DECL_FIELD |
| line 172 | then branch 171-173 in if 171-174 in elsif branch 170-175 in if 168-176 in case alternative S_IDLE 166-176 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Used in an if condition (host_req_i.amo = '1') inside a sequential if statement. | ctrl.state = S_IDLE AND not ((host_req_i.fence = '1') or (ctrl.buf_sync = '1')) AND (host_req_i.stb = '1') or (ctrl.buf_req = '1') | IF_COND |

### host_req_i.amoop

from validate

| Occurrence Lines | Context | Path | SITE Tagged |
| --- | --- | --- | --- |
| line 37 | port clause 34-41 in entity 27-42; Declaration of the field via the base's port declaration; the record type is declared outside this source. | - | DECL_FIELD |

### host_req_i.lock

from validate

| Occurrence Lines | Context | Path | SITE Tagged |
| --- | --- | --- | --- |
| line 37 | port clause 34-41 in entity 27-42; Declaration of the field via the base's port declaration; the record type is declared outside this source. | - | DECL_FIELD |

### host_req_i.fence

from validate

| Occurrence Lines | Context | Path | SITE Tagged |
| --- | --- | --- | --- |
| line 37 | port clause 34-41 in entity 27-42; Declaration of the field via the base's port declaration; the record type is declared outside this source. | - | DECL_FIELD |
| line 138 | process ctrl_engine_comb 133-268 in architecture 44-294; Operand on the right-hand side of a sequential signal assignment joined by an operator (ctrl_nxt.buf_sync <= ctrl.buf_sync or host_req_i.fence). | - | RHS_OPERAND |
| line 168 | then branch 168-169 in if 168-176 in case alternative S_IDLE 166-176 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Used in an if condition (host_req_i.fence = '1') inside a sequential if statement. | ctrl.state = S_IDLE | IF_COND |

### host_rsp_o

from validate

| Occurrence Lines | Context | Path | SITE Tagged |
| --- | --- | --- | --- |
| line 38 | port clause 34-41 in entity 27-42; Declared as a port in the entity's port clause. | - | DECL_PORT |
| line 154 | process ctrl_engine_comb 133-268 in architecture 44-294; Record base; field reached: ack. | - | FIELD_USE |
| line 155 | process ctrl_engine_comb 133-268 in architecture 44-294; Record base; field reached: err. | - | FIELD_USE |
| line 156 | process ctrl_engine_comb 133-268 in architecture 44-294; Record base; field reached: data. | - | FIELD_USE |
| line 191 | then branch 190-192 in if 190-197 in elsif branch 189-197 in if 186-205 in case alternative S_LOOKUP 178-205 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Record base; field reached: ack. | ctrl.state = S_LOOKUP AND not (ctrl.buf_dir = '1') AND cache_i.sta_hit = '1' AND (host_req_i.rw = '0') or (READ_ONLY = true) | FIELD_USE |
| line 209 | case alternative S_DIRECT_RSP 207-212 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Target of a sequential signal assignment (whole record) on the left-hand side of <= inside a process. | ctrl.state = S_DIRECT_RSP | LHS_PROC |
| line 256 | then branch 254-258 in if 254-261 in case alternative S_DOWNLOAD_DONE 252-261 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Record base; field reached: ack. | ctrl.state = S_DOWNLOAD_DONE AND ctrl.buf_err = '1' | FIELD_USE |
| line 257 | then branch 254-258 in if 254-261 in case alternative S_DOWNLOAD_DONE 252-261 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Record base; field reached: err. | ctrl.state = S_DOWNLOAD_DONE AND ctrl.buf_err = '1' | FIELD_USE |

### host_rsp_o.ack

from validate

| Occurrence Lines | Context | Path | SITE Tagged |
| --- | --- | --- | --- |
| line 38 | port clause 34-41 in entity 27-42; Declaration of the field via the base's port declaration; the record type is declared outside this source. | - | DECL_FIELD |
| line 154 | process ctrl_engine_comb 133-268 in architecture 44-294; Target on the left-hand side of a sequential signal assignment inside a process (host_rsp_o.ack <= '0'). | - | LHS_PROC |
| line 191 | then branch 190-192 in if 190-197 in elsif branch 189-197 in if 186-205 in case alternative S_LOOKUP 178-205 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Target on the left-hand side of a sequential signal assignment inside a process (host_rsp_o.ack <= '1'). | ctrl.state = S_LOOKUP AND not (ctrl.buf_dir = '1') AND cache_i.sta_hit = '1' AND (host_req_i.rw = '0') or (READ_ONLY = true) | LHS_PROC |
| line 256 | then branch 254-258 in if 254-261 in case alternative S_DOWNLOAD_DONE 252-261 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Target on the left-hand side of a sequential signal assignment inside a process (host_rsp_o.ack <= '1'). | ctrl.state = S_DOWNLOAD_DONE AND ctrl.buf_err = '1' | LHS_PROC |

### host_rsp_o.err

from validate

| Occurrence Lines | Context | Path | SITE Tagged |
| --- | --- | --- | --- |
| line 38 | port clause 34-41 in entity 27-42; Declaration of the field via the base's port declaration; the record type is declared outside this source. | - | DECL_FIELD |
| line 155 | process ctrl_engine_comb 133-268 in architecture 44-294; Target on the left-hand side of a sequential signal assignment inside a process (host_rsp_o.err <= '0'). | - | LHS_PROC |
| line 257 | then branch 254-258 in if 254-261 in case alternative S_DOWNLOAD_DONE 252-261 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Target on the left-hand side of a sequential signal assignment inside a process (host_rsp_o.err <= '1'). | ctrl.state = S_DOWNLOAD_DONE AND ctrl.buf_err = '1' | LHS_PROC |

### host_rsp_o.data

from validate

| Occurrence Lines | Context | Path | SITE Tagged |
| --- | --- | --- | --- |
| line 38 | port clause 34-41 in entity 27-42; Declaration of the field via the base's port declaration; the record type is declared outside this source. | - | DECL_FIELD |
| line 156 | process ctrl_engine_comb 133-268 in architecture 44-294; Target on the left-hand side of a sequential signal assignment inside a process (host_rsp_o.data <= cache_i.data). | - | LHS_PROC |

### bus_req_o

from validate

| Occurrence Lines | Context | Path | SITE Tagged |
| --- | --- | --- | --- |
| line 39 | port clause 34-41 in entity 27-42; Declared as a port in the entity's port clause. | - | DECL_PORT |
| line 159 | process ctrl_engine_comb 133-268 in architecture 44-294; Target of a sequential signal assignment (whole left-hand side of <= inside a process). | - | LHS_PROC |
| line 160 | process ctrl_engine_comb 133-268 in architecture 44-294; Record base; field reached: stb. | - | FIELD_USE |
| line 161 | process ctrl_engine_comb 133-268 in architecture 44-294; Record base; field reached: fence. | - | FIELD_USE |
| line 187 | then branch 186-188 in if 186-205 in case alternative S_LOOKUP 178-205 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Record base; field reached: stb. | ctrl.state = S_LOOKUP AND ctrl.buf_dir = '1' | FIELD_USE |
| line 195 | else branch 193-196 in if 190-197 in elsif branch 189-197 in if 186-205 in case alternative S_LOOKUP 178-205 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Record base; field reached: stb. | ctrl.state = S_LOOKUP AND not (ctrl.buf_dir = '1') AND cache_i.sta_hit = '1' AND not ((host_req_i.rw = '0') or (READ_ONLY = true)) | FIELD_USE |
| line 202 | else branch 201-203 in if 199-204 in else branch 198-204 in if 186-205 in case alternative S_LOOKUP 178-205 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Record base; field reached: stb. | ctrl.state = S_LOOKUP AND not (ctrl.buf_dir = '1') AND not (cache_i.sta_hit = '1') AND not ((host_req_i.rw = '0') or (READ_ONLY = true)) | FIELD_USE |
| line 217 | then branch 216-217 in if 216-218 in case alternative S_CLEAR 214-221 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Record base; field reached: fence. | ctrl.state = S_CLEAR AND [static] READ_ONLY = false | FIELD_USE |
| line 227 | case alternative S_DOWNLOAD_REQ 223-231 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Record base; field reached: addr (target of a sequential signal assignment to the field). | ctrl.state = S_DOWNLOAD_REQ | FIELD_USE |
| line 228 | case alternative S_DOWNLOAD_REQ 223-231 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Record base; field reached: rw (target of a sequential signal assignment to the field). | ctrl.state = S_DOWNLOAD_REQ | FIELD_USE |
| line 229 | case alternative S_DOWNLOAD_REQ 223-231 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Record base; field reached: stb (target of a sequential signal assignment to the field). | ctrl.state = S_DOWNLOAD_REQ | FIELD_USE |
| line 230 | case alternative S_DOWNLOAD_REQ 223-231 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Record base; field reached: lock (target of a sequential signal assignment to the field). | ctrl.state = S_DOWNLOAD_REQ | FIELD_USE |
| line 238 | case alternative S_DOWNLOAD_RSP 233-250 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Record base; field reached: addr (target of a sequential signal assignment to the field). | ctrl.state = S_DOWNLOAD_RSP | FIELD_USE |
| line 239 | case alternative S_DOWNLOAD_RSP 233-250 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Record base; field reached: rw (target of a sequential signal assignment to the field). | ctrl.state = S_DOWNLOAD_RSP | FIELD_USE |
| line 240 | case alternative S_DOWNLOAD_RSP 233-250 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Record base; field reached: lock (target of a sequential signal assignment to the field). | ctrl.state = S_DOWNLOAD_RSP | FIELD_USE |

### bus_req_o.addr

from validate

| Occurrence Lines | Context | Path | SITE Tagged |
| --- | --- | --- | --- |
| line 39 | port clause 34-41 in entity 27-42; Port declaration of the base that declares this field; record type declared outside this source. | - | DECL_FIELD |
| line 227 | case alternative S_DOWNLOAD_REQ 223-231 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Sequential signal assignment target: the field is the left-hand side of a signal assignment inside a process. | ctrl.state = S_DOWNLOAD_REQ | LHS_PROC |
| line 238 | case alternative S_DOWNLOAD_RSP 233-250 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Sequential signal assignment target: the field is the left-hand side of a signal assignment inside a process. | ctrl.state = S_DOWNLOAD_RSP | LHS_PROC |

### bus_req_o.data

from validate

| Occurrence Lines | Context | Path | SITE Tagged |
| --- | --- | --- | --- |
| line 39 | port clause 34-41 in entity 27-42; Port declaration of the base that declares this field; record type declared outside this source. | - | DECL_FIELD |

### bus_req_o.ben

from validate

| Occurrence Lines | Context | Path | SITE Tagged |
| --- | --- | --- | --- |
| line 39 | port clause 34-41 in entity 27-42; Port declaration of the base that declares this field; record type declared outside this source. | - | DECL_FIELD |

### bus_req_o.stb

from validate

| Occurrence Lines | Context | Path | SITE Tagged |
| --- | --- | --- | --- |
| line 39 | port clause 34-41 in entity 27-42; Port declaration of the base that declares this field; record type declared outside this source. | - | DECL_FIELD |
| line 160 | process ctrl_engine_comb 133-268 in architecture 44-294; Sequential signal assignment target: the field is the left-hand side of a signal assignment inside a process. | - | LHS_PROC |
| line 187 | then branch 186-188 in if 186-205 in case alternative S_LOOKUP 178-205 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Sequential signal assignment target: the field is the left-hand side of a signal assignment inside a process. | ctrl.state = S_LOOKUP AND ctrl.buf_dir = '1' | LHS_PROC |
| line 195 | else branch 193-196 in if 190-197 in elsif branch 189-197 in if 186-205 in case alternative S_LOOKUP 178-205 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Sequential signal assignment target: the field is the left-hand side of a signal assignment inside a process. | ctrl.state = S_LOOKUP AND not (ctrl.buf_dir = '1') AND cache_i.sta_hit = '1' AND not ((host_req_i.rw = '0') or (READ_ONLY = true)) | LHS_PROC |
| line 202 | else branch 201-203 in if 199-204 in else branch 198-204 in if 186-205 in case alternative S_LOOKUP 178-205 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Sequential signal assignment target: the field is the left-hand side of a signal assignment inside a process. | ctrl.state = S_LOOKUP AND not (ctrl.buf_dir = '1') AND not (cache_i.sta_hit = '1') AND not ((host_req_i.rw = '0') or (READ_ONLY = true)) | LHS_PROC |
| line 229 | case alternative S_DOWNLOAD_REQ 223-231 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Sequential signal assignment target: the field is the left-hand side of a signal assignment inside a process. | ctrl.state = S_DOWNLOAD_REQ | LHS_PROC |

### bus_req_o.rw

from validate

| Occurrence Lines | Context | Path | SITE Tagged |
| --- | --- | --- | --- |
| line 39 | port clause 34-41 in entity 27-42; Port declaration of the base that declares this field; record type declared outside this source. | - | DECL_FIELD |
| line 228 | case alternative S_DOWNLOAD_REQ 223-231 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Sequential signal assignment target: the field is the left-hand side of a signal assignment inside a process. | ctrl.state = S_DOWNLOAD_REQ | LHS_PROC |
| line 239 | case alternative S_DOWNLOAD_RSP 233-250 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Sequential signal assignment target: the field is the left-hand side of a signal assignment inside a process. | ctrl.state = S_DOWNLOAD_RSP | LHS_PROC |

### bus_req_o.src

from validate

| Occurrence Lines | Context | Path | SITE Tagged |
| --- | --- | --- | --- |
| line 39 | port clause 34-41 in entity 27-42; Port declaration of the base that declares this field; record type declared outside this source. | - | DECL_FIELD |

### bus_req_o.priv

from validate

| Occurrence Lines | Context | Path | SITE Tagged |
| --- | --- | --- | --- |
| line 39 | port clause 34-41 in entity 27-42; Port declaration of the base that declares this field; record type declared outside this source. | - | DECL_FIELD |

### bus_req_o.debug

from validate

| Occurrence Lines | Context | Path | SITE Tagged |
| --- | --- | --- | --- |
| line 39 | port clause 34-41 in entity 27-42; Port declaration of the base that declares this field; record type declared outside this source. | - | DECL_FIELD |

### bus_req_o.amo

from validate

| Occurrence Lines | Context | Path | SITE Tagged |
| --- | --- | --- | --- |
| line 39 | port clause 34-41 in entity 27-42; Port declaration of the base that declares this field; record type declared outside this source. | - | DECL_FIELD |

### bus_req_o.amoop

from validate

| Occurrence Lines | Context | Path | SITE Tagged |
| --- | --- | --- | --- |
| line 39 | port clause 34-41 in entity 27-42; Port declaration of the base that declares this field; record type declared outside this source. | - | DECL_FIELD |

### bus_req_o.lock

from validate

| Occurrence Lines | Context | Path | SITE Tagged |
| --- | --- | --- | --- |
| line 39 | port clause 34-41 in entity 27-42; Port declaration of the base that declares this field; record type declared outside this source. | - | DECL_FIELD |
| line 230 | case alternative S_DOWNLOAD_REQ 223-231 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Sequential signal assignment target: the field is the left-hand side of a signal assignment inside a process. | ctrl.state = S_DOWNLOAD_REQ | LHS_PROC |
| line 240 | case alternative S_DOWNLOAD_RSP 233-250 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Sequential signal assignment target: the field is the left-hand side of a signal assignment inside a process. | ctrl.state = S_DOWNLOAD_RSP | LHS_PROC |

### bus_req_o.fence

from validate

| Occurrence Lines | Context | Path | SITE Tagged |
| --- | --- | --- | --- |
| line 39 | port clause 34-41 in entity 27-42; Port declaration of the base that declares this field; record type declared outside this source. | - | DECL_FIELD |
| line 161 | process ctrl_engine_comb 133-268 in architecture 44-294; Sequential signal assignment target: the field is the left-hand side of a signal assignment inside a process. | - | LHS_PROC |
| line 217 | then branch 216-217 in if 216-218 in case alternative S_CLEAR 214-221 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Sequential signal assignment target inside the S_CLEAR branch: the field is the left-hand side of a signal assignment inside a process. | ctrl.state = S_CLEAR AND [static] READ_ONLY = false | LHS_PROC |

### bus_rsp_i

from validate

| Occurrence Lines | Context | Path | SITE Tagged |
| --- | --- | --- | --- |
| line 40 | port clause 34-41 in entity 27-42; Port declaration of this element (the port itself). | - | DECL_PORT |
| line 133 | process ctrl_engine_comb 133-268 in architecture 44-294; Named in the sensitivity list of the process header. | - | PROCESS_TRIG |
| line 209 | case alternative S_DIRECT_RSP 207-212 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Sequential signal assignment whole right-hand side: the base is the entire RHS of a signal assignment inside a process. | ctrl.state = S_DIRECT_RSP | DIRR_ASS |
| line 210 | then branch 210-211 in if 210-212 in case alternative S_DIRECT_RSP 207-212 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Field use: the base is used to reach field ack. | ctrl.state = S_DIRECT_RSP | FIELD_USE |
| line 236 | case alternative S_DOWNLOAD_RSP 233-250 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Field use: the base is used to reach field data. | ctrl.state = S_DOWNLOAD_RSP | FIELD_USE |
| line 242 | case alternative S_DOWNLOAD_RSP 233-250 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Field use: the base is used to reach field err. | ctrl.state = S_DOWNLOAD_RSP | FIELD_USE |
| line 243 | then branch 243-249 in if 243-250 in case alternative S_DOWNLOAD_RSP 233-250 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Field use: the base is used to reach field ack. | ctrl.state = S_DOWNLOAD_RSP | FIELD_USE |

### bus_rsp_i.ack

from validate

| Occurrence Lines | Context | Path | SITE Tagged |
| --- | --- | --- | --- |
| line 40 | port clause 34-41 in entity 27-42; Port declaration of the base that declares this field; record type declared outside this source. | - | DECL_FIELD |
| line 210 | then branch 210-211 in if 210-212 in case alternative S_DIRECT_RSP 207-212 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Condition of an if statement (not an edge): the field ack is tested in the if condition inside a process. | ctrl.state = S_DIRECT_RSP | IF_COND |
| line 243 | then branch 243-249 in if 243-250 in case alternative S_DOWNLOAD_RSP 233-250 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Condition of an if statement (not an edge): the field ack is tested in the if condition inside a process. | ctrl.state = S_DOWNLOAD_RSP | IF_COND |

### bus_rsp_i.err

from validate

| Occurrence Lines | Context | Path | SITE Tagged |
| --- | --- | --- | --- |
| line 40 | port clause 34-41 in entity 27-42; Port declaration of the base that declares this field; record type declared outside this source. | - | DECL_FIELD |
| line 242 | case alternative S_DOWNLOAD_RSP 233-250 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Right-hand side operand: the field appears on the RHS of a signal assignment and is joined to another operand by an operator (or). | ctrl.state = S_DOWNLOAD_RSP | RHS_OPERAND |

### bus_rsp_i.data

from validate

| Occurrence Lines | Context | Path | SITE Tagged |
| --- | --- | --- | --- |
| line 40 | port clause 34-41 in entity 27-42; Port declaration of the base that declares this field; record type declared outside this source. | - | DECL_FIELD |
| line 236 | case alternative S_DOWNLOAD_RSP 233-250 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Sequential signal assignment whole right-hand side: the field is the entire RHS of a signal assignment inside a process. | ctrl.state = S_DOWNLOAD_RSP | DIRR_ASS |

### cache_o

from validate

| Occurrence Lines | Context | Path | SITE Tagged |
| --- | --- | --- | --- |
| line 84 | declarative part 47-108 in architecture 44-294; Signal declaration of this record-typed signal. | - | DECL_SIGNAL |
| line 146 | process ctrl_engine_comb 133-268 in architecture 44-294; Field use: reaches field cmd_clr. | - | FIELD_USE |
| line 147 | process ctrl_engine_comb 133-268 in architecture 44-294; Field use: reaches field cmd_inv. | - | FIELD_USE |
| line 148 | process ctrl_engine_comb 133-268 in architecture 44-294; Field use: reaches field cmd_new. | - | FIELD_USE |
| line 149 | process ctrl_engine_comb 133-268 in architecture 44-294; Field use: reaches field addr. | - | FIELD_USE |
| line 150 | process ctrl_engine_comb 133-268 in architecture 44-294; Field use: reaches field we. | - | FIELD_USE |
| line 151 | process ctrl_engine_comb 133-268 in architecture 44-294; Field use: reaches field data. | - | FIELD_USE |
| line 194 | else branch 193-196 in if 190-197 in elsif branch 189-197 in if 186-205 in case alternative S_LOOKUP 178-205 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Field use: reaches field we. | ctrl.state = S_LOOKUP AND not (ctrl.buf_dir = '1') AND cache_i.sta_hit = '1' AND not ((host_req_i.rw = '0') or (READ_ONLY = true)) | FIELD_USE |
| line 219 | case alternative S_CLEAR 214-221 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Field use: reaches field cmd_clr. | ctrl.state = S_CLEAR | FIELD_USE |
| line 225 | case alternative S_DOWNLOAD_REQ 223-231 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Field use: reaches field addr. | ctrl.state = S_DOWNLOAD_REQ | FIELD_USE |
| line 226 | case alternative S_DOWNLOAD_REQ 223-231 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Field use: reaches field cmd_new. | ctrl.state = S_DOWNLOAD_REQ | FIELD_USE |
| line 235 | case alternative S_DOWNLOAD_RSP 233-250 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Field use: reaches field addr. | ctrl.state = S_DOWNLOAD_RSP | FIELD_USE |
| line 236 | case alternative S_DOWNLOAD_RSP 233-250 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Field use: reaches field data. | ctrl.state = S_DOWNLOAD_RSP | FIELD_USE |
| line 237 | case alternative S_DOWNLOAD_RSP 233-250 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Field use: reaches field we. | ctrl.state = S_DOWNLOAD_RSP | FIELD_USE |
| line 255 | then branch 254-258 in if 254-261 in case alternative S_DOWNLOAD_DONE 252-261 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Field use: reaches field cmd_inv. | ctrl.state = S_DOWNLOAD_DONE AND ctrl.buf_err = '1' | FIELD_USE |
| line 283 | port map 278-292 in instance neorv32_cache_memory_inst 273-292 in architecture 44-294; Field use in an instance association: reaches field cmd_clr in the port map actual. | - | FIELD_USE |
| line 284 | port map 278-292 in instance neorv32_cache_memory_inst 273-292 in architecture 44-294; Field use in an instance association: reaches field cmd_inv in the port map actual. | - | FIELD_USE |
| line 285 | port map 278-292 in instance neorv32_cache_memory_inst 273-292 in architecture 44-294; Field use in an instance association: reaches field cmd_new in the port map actual. | - | FIELD_USE |
| line 288 | port map 278-292 in instance neorv32_cache_memory_inst 273-292 in architecture 44-294; Field use in an instance association: reaches field addr in the port map actual. | - | FIELD_USE |
| line 289 | port map 278-292 in instance neorv32_cache_memory_inst 273-292 in architecture 44-294; Field use in an instance association: reaches field we in the port map actual. | - | FIELD_USE |
| line 290 | port map 278-292 in instance neorv32_cache_memory_inst 273-292 in architecture 44-294; Field use in an instance association: reaches field data in the port map actual. | - | FIELD_USE |

### cache_o.cmd_clr

from validate

| Occurrence Lines | Context | Path | SITE Tagged |
| --- | --- | --- | --- |
| line 84 | declarative part 47-108 in architecture 44-294; Declaration of the base that declares this field; record type declared in this source. | - | DECL_FIELD |
| line 146 | process ctrl_engine_comb 133-268 in architecture 44-294; Sequential signal assignment target: the field is the left-hand side of a signal assignment inside a process. | - | LHS_PROC |
| line 219 | case alternative S_CLEAR 214-221 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Sequential signal assignment target inside the S_CLEAR branch: the field is the left-hand side of a signal assignment inside a process. | ctrl.state = S_CLEAR | LHS_PROC |
| line 283 | port map 278-292 in instance neorv32_cache_memory_inst 273-292 in architecture 44-294; Actual in a port map association: the field is the actual associated with formal rstn_i of the instance. | - | ASSOC_ACTUAL |

### cache_o.cmd_inv

from validate

| Occurrence Lines | Context | Path | SITE Tagged |
| --- | --- | --- | --- |
| line 84 | declarative part 47-108 in architecture 44-294; Declaration of the base that declares this field; record type declared in this source. | - | DECL_FIELD |
| line 147 | process ctrl_engine_comb 133-268 in architecture 44-294; Sequential signal assignment target: the field is the left-hand side of a signal assignment inside a process. | - | LHS_PROC |
| line 255 | then branch 254-258 in if 254-261 in case alternative S_DOWNLOAD_DONE 252-261 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Sequential signal assignment target inside the S_DOWNLOAD_DONE then branch: the field is the left-hand side of a signal assignment inside a process. | ctrl.state = S_DOWNLOAD_DONE AND ctrl.buf_err = '1' | LHS_PROC |
| line 284 | port map 278-292 in instance neorv32_cache_memory_inst 273-292 in architecture 44-294; Actual in a port map association: the field is the actual associated with formal inv_i of the instance. | - | ASSOC_ACTUAL |

### cache_o.cmd_new

from validate

| Occurrence Lines | Context | Path | SITE Tagged |
| --- | --- | --- | --- |
| line 84 | declarative part 47-108 in architecture 44-294; Declaration of the base that declares this field; record type declared in this source. | - | DECL_FIELD |
| line 148 | process ctrl_engine_comb 133-268 in architecture 44-294; Sequential signal assignment target: the field is the left-hand side of a signal assignment inside a process. | - | LHS_PROC |
| line 226 | case alternative S_DOWNLOAD_REQ 223-231 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Sequential signal assignment target inside the S_DOWNLOAD_REQ branch: the field is the left-hand side of a signal assignment inside a process. | ctrl.state = S_DOWNLOAD_REQ | LHS_PROC |
| line 285 | port map 278-292 in instance neorv32_cache_memory_inst 273-292 in architecture 44-294; Actual in a port map association: the field is the actual associated with formal new_i of the instance. | - | ASSOC_ACTUAL |

### cache_o.addr

from validate

| Occurrence Lines | Context | Path | SITE Tagged |
| --- | --- | --- | --- |
| line 84 | declarative part 47-108 in architecture 44-294; The base that declares this field; the port/signal statement declares the record that contains the field. The record type is declared in this source. | - | DECL_FIELD |
| line 149 | process ctrl_engine_comb 133-268 in architecture 44-294; Target of a signal assignment inside a process; the record field written as the assignment target. | - | LHS_PROC |
| line 225 | case alternative S_DOWNLOAD_REQ 223-231 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Target of a signal assignment inside a process (case alternative S_DOWNLOAD_REQ); the record field written as the assignment target. | ctrl.state = S_DOWNLOAD_REQ | LHS_PROC |
| line 235 | case alternative S_DOWNLOAD_RSP 233-250 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Target of a signal assignment inside a process (case alternative S_DOWNLOAD_RSP); the record field written as the assignment target. | ctrl.state = S_DOWNLOAD_RSP | LHS_PROC |
| line 288 | port map 278-292 in instance neorv32_cache_memory_inst 273-292 in architecture 44-294; Actual in a port map association; the record field is the actual associated with formal addr_i. | - | ASSOC_ACTUAL |

### cache_o.data

from validate

| Occurrence Lines | Context | Path | SITE Tagged |
| --- | --- | --- | --- |
| line 84 | declarative part 47-108 in architecture 44-294; The base that declares this field; the port/signal statement declares the record that contains the field. The record type is declared in this source. | - | DECL_FIELD |
| line 151 | process ctrl_engine_comb 133-268 in architecture 44-294; Target of a signal assignment inside a process; the record field written as the assignment target. | - | LHS_PROC |
| line 236 | case alternative S_DOWNLOAD_RSP 233-250 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Target of a signal assignment inside a process (case alternative S_DOWNLOAD_RSP); the record field written as the assignment target. | ctrl.state = S_DOWNLOAD_RSP | LHS_PROC |
| line 290 | port map 278-292 in instance neorv32_cache_memory_inst 273-292 in architecture 44-294; Actual in a port map association; the record field is the actual associated with formal wdata_i. | - | ASSOC_ACTUAL |

### cache_o.we

from validate

| Occurrence Lines | Context | Path | SITE Tagged |
| --- | --- | --- | --- |
| line 84 | declarative part 47-108 in architecture 44-294; The base that declares this field; the port/signal statement declares the record that contains the field. The record type is declared in this source. | - | DECL_FIELD |
| line 150 | process ctrl_engine_comb 133-268 in architecture 44-294; Target of a signal assignment inside a process; the record field written as the assignment target. | - | LHS_PROC |
| line 194 | else branch 193-196 in if 190-197 in elsif branch 189-197 in if 186-205 in case alternative S_LOOKUP 178-205 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Target of a signal assignment inside a process (in a branch); the record field written as the assignment target. | ctrl.state = S_LOOKUP AND not (ctrl.buf_dir = '1') AND cache_i.sta_hit = '1' AND not ((host_req_i.rw = '0') or (READ_ONLY = true)) | LHS_PROC |
| line 237 | case alternative S_DOWNLOAD_RSP 233-250 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Target of a signal assignment inside a process (case alternative S_DOWNLOAD_RSP); the record field written as the assignment target. | ctrl.state = S_DOWNLOAD_RSP | LHS_PROC |
| line 289 | port map 278-292 in instance neorv32_cache_memory_inst 273-292 in architecture 44-294; Actual in a port map association; the record field is the actual associated with formal we_i. | - | ASSOC_ACTUAL |

### cache_i

from validate

| Occurrence Lines | Context | Path | SITE Tagged |
| --- | --- | --- | --- |
| line 91 | declarative part 47-108 in architecture 44-294; Signal declaration of the record-typed signal cache_i. | - | DECL_SIGNAL |
| line 133 | process ctrl_engine_comb 133-268 in architecture 44-294; Occurrence in the sensitivity list of a process statement header. | - | PROCESS_TRIG |
| line 156 | process ctrl_engine_comb 133-268 in architecture 44-294; Base of a record field selection reaching field data in the statement 'host_rsp_o.data <= cache_i.data;'. | - | FIELD_USE |
| line 189 | elsif branch 189-197 in if 186-205 in case alternative S_LOOKUP 178-205 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Base of a record field selection reaching field sta_hit in the if condition 'elsif (cache_i.sta_hit = '1') then'. | ctrl.state = S_LOOKUP AND not (ctrl.buf_dir = '1') | FIELD_USE |
| line 286 | port map 278-292 in instance neorv32_cache_memory_inst 273-292 in architecture 44-294; Base of a record field selection reaching field sta_hit in the port map actual 'hit_o => cache_i.sta_hit'. | - | FIELD_USE |
| line 291 | port map 278-292 in instance neorv32_cache_memory_inst 273-292 in architecture 44-294; Base of a record field selection reaching field data in the port map actual 'rdata_o => cache_i.data'. | - | FIELD_USE |

### cache_i.sta_hit

from validate

| Occurrence Lines | Context | Path | SITE Tagged |
| --- | --- | --- | --- |
| line 91 | declarative part 47-108 in architecture 44-294; The field's declaration is the signal declaration of the base; the record type is declared in this source. | - | DECL_FIELD |
| line 189 | elsif branch 189-197 in if 186-205 in case alternative S_LOOKUP 178-205 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Element in the condition of an elsif (if statement); the field appears in the if/elsif condition. | ctrl.state = S_LOOKUP AND not (ctrl.buf_dir = '1') | IF_COND |
| line 286 | port map 278-292 in instance neorv32_cache_memory_inst 273-292 in architecture 44-294; Actual in a port map association; the record field is the actual associated with formal hit_o. | - | ASSOC_ACTUAL |

### cache_i.data

from validate

| Occurrence Lines | Context | Path | SITE Tagged |
| --- | --- | --- | --- |
| line 91 | declarative part 47-108 in architecture 44-294; The field's declaration is the signal declaration of the base; the record type is declared in this source. | - | DECL_FIELD |
| line 156 | process ctrl_engine_comb 133-268 in architecture 44-294; The whole right-hand side of a signal assignment inside a process; the right-hand side is exactly the field 'cache_i.data'. | - | DIRR_ASS |
| line 291 | port map 278-292 in instance neorv32_cache_memory_inst 273-292 in architecture 44-294; Actual in a port map association; the record field is the actual associated with formal rdata_o. | - | ASSOC_ACTUAL |

### ctrl

from validate

| Occurrence Lines | Context | Path | SITE Tagged |
| --- | --- | --- | --- |
| line 108 | declarative part 47-108 in architecture 44-294; Signal declaration of the record-typed signal ctrl. | - | DECL_SIGNAL |
| line 117 | then branch 116-124 in if 116-127 in process ctrl_engine_sync 114-128 in architecture 44-294; Base of a record field selection reaching field state in the sequential assignment 'ctrl.state <= S_IDLE;'. | rstn_i = '0' | FIELD_USE |
| line 118 | then branch 116-124 in if 116-127 in process ctrl_engine_sync 114-128 in architecture 44-294; Base of a record field selection reaching field buf_req in the sequential assignment 'ctrl.buf_req <= '0';'. | rstn_i = '0' | FIELD_USE |
| line 119 | then branch 116-124 in if 116-127 in process ctrl_engine_sync 114-128 in architecture 44-294; Base of a record field selection reaching field buf_sync in the sequential assignment 'ctrl.buf_sync <= '0';'. | rstn_i = '0' | FIELD_USE |
| line 120 | then branch 116-124 in if 116-127 in process ctrl_engine_sync 114-128 in architecture 44-294; Base of a record field selection reaching field buf_err in the sequential assignment 'ctrl.buf_err <= '0';'. | rstn_i = '0' | FIELD_USE |
| line 121 | then branch 116-124 in if 116-127 in process ctrl_engine_sync 114-128 in architecture 44-294; Base of a record field selection reaching field buf_dir in the sequential assignment 'ctrl.buf_dir <= '0';'. | rstn_i = '0' | FIELD_USE |
| line 122 | then branch 116-124 in if 116-127 in process ctrl_engine_sync 114-128 in architecture 44-294; Base of a record field selection reaching field tag in the sequential assignment 'ctrl.tag <= (others => '0');'. | rstn_i = '0' | FIELD_USE |
| line 123 | then branch 116-124 in if 116-127 in process ctrl_engine_sync 114-128 in architecture 44-294; Base of a record field selection reaching field idx in the sequential assignment 'ctrl.idx <= (others => '0');'. | rstn_i = '0' | FIELD_USE |
| line 124 | then branch 116-124 in if 116-127 in process ctrl_engine_sync 114-128 in architecture 44-294; Base of a record field selection reaching field ofs in the sequential assignment 'ctrl.ofs <= (others => '0');'. | rstn_i = '0' | FIELD_USE |
| line 126 | elsif branch 125-126 in if 116-127 in process ctrl_engine_sync 114-128 in architecture 44-294; Target of a signal assignment inside a process; the whole record ctrl is the assignment target 'ctrl <= ctrl_nxt;'. | not (rstn_i = '0') AND rising_edge(clk_i) | LHS_PROC |
| line 133 | process ctrl_engine_comb 133-268 in architecture 44-294; Occurrence of the signal in the sensitivity list of a process statement header. | - | PROCESS_TRIG |
| line 136 | process ctrl_engine_comb 133-268 in architecture 44-294; Base of a record field selection reaching field state in the assignment 'ctrl_nxt.state <= ctrl.state;'. | - | FIELD_USE |
| line 137 | process ctrl_engine_comb 133-268 in architecture 44-294; Base of a record field selection reaching field buf_req in the expression 'ctrl_nxt.buf_req <= ctrl.buf_req or host_req_i.stb;'. | - | FIELD_USE |
| line 138 | process ctrl_engine_comb 133-268 in architecture 44-294; Base of a record field selection reaching field buf_sync in the expression 'ctrl_nxt.buf_sync <= ctrl.buf_sync or host_req_i.fence;'. | - | FIELD_USE |
| line 139 | process ctrl_engine_comb 133-268 in architecture 44-294; Base of a record field selection reaching field buf_err in the assignment 'ctrl_nxt.buf_err <= ctrl.buf_err;'. | - | FIELD_USE |
| line 141 | process ctrl_engine_comb 133-268 in architecture 44-294; Base of a record field selection reaching field tag in the assignment 'ctrl_nxt.tag <= ctrl.tag;'. | - | FIELD_USE |
| line 142 | process ctrl_engine_comb 133-268 in architecture 44-294; Base of a record field selection reaching field idx in the assignment 'ctrl_nxt.idx <= ctrl.idx;'. | - | FIELD_USE |
| line 143 | process ctrl_engine_comb 133-268 in architecture 44-294; Base of a record field selection reaching field ofs in the assignment 'ctrl_nxt.ofs <= ctrl.ofs;'. | - | FIELD_USE |
| line 164 | case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Base of a case expression selection reaching field state in the statement 'case ctrl.state is'. | - | FIELD_USE |
| line 168 | then branch 168-169 in if 168-176 in case alternative S_IDLE 166-176 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Base of a record field selection reaching field buf_sync in the if condition '(host_req_i.fence = '1') or (ctrl.buf_sync = '1')'. | ctrl.state = S_IDLE | FIELD_USE |
| line 170 | elsif branch 170-175 in if 168-176 in case alternative S_IDLE 166-176 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Base of a record field selection reaching field buf_req in the elsif condition '(host_req_i.stb = '1') or (ctrl.buf_req = '1')'. | ctrl.state = S_IDLE AND not ((host_req_i.fence = '1') or (ctrl.buf_sync = '1')) | FIELD_USE |
| line 186 | then branch 186-188 in if 186-205 in case alternative S_LOOKUP 178-205 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Base of a record field selection reaching field buf_dir in the if condition 'if (ctrl.buf_dir = '1') then'. | ctrl.state = S_LOOKUP | FIELD_USE |
| line 225 | case alternative S_DOWNLOAD_REQ 223-231 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Base of a record field selection reaching field tag in the right-hand side concatenation 'ctrl.tag & ctrl.idx & ctrl.ofs & "00"'. | ctrl.state = S_DOWNLOAD_REQ | FIELD_USE |
| line 225 | case alternative S_DOWNLOAD_REQ 223-231 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Base of a record field selection reaching field idx in the right-hand side concatenation 'ctrl.tag & ctrl.idx & ctrl.ofs & "00"'. | ctrl.state = S_DOWNLOAD_REQ | FIELD_USE |
| line 225 | case alternative S_DOWNLOAD_REQ 223-231 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Base of a record field selection reaching field ofs in the right-hand side concatenation 'ctrl.tag & ctrl.idx & ctrl.ofs & "00"'. | ctrl.state = S_DOWNLOAD_REQ | FIELD_USE |
| line 227 | case alternative S_DOWNLOAD_REQ 223-231 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Base of a record field selection reaching field tag in the right-hand side concatenation 'ctrl.tag & ctrl.idx & ctrl.ofs & "00"' of the assignment to bus_req_o.addr. | ctrl.state = S_DOWNLOAD_REQ | FIELD_USE |
| line 227 | case alternative S_DOWNLOAD_REQ 223-231 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Base of a record field selection reaching field idx in the right-hand side concatenation 'ctrl.tag & ctrl.idx & ctrl.ofs & "00"' of the assignment to bus_req_o.addr. | ctrl.state = S_DOWNLOAD_REQ | FIELD_USE |
| line 227 | case alternative S_DOWNLOAD_REQ 223-231 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Base of a record field selection reaching field ofs in the right-hand side concatenation 'ctrl.tag & ctrl.idx & ctrl.ofs & "00"' of the assignment to bus_req_o.addr. | ctrl.state = S_DOWNLOAD_REQ | FIELD_USE |
| line 235 | case alternative S_DOWNLOAD_RSP 233-250 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Base of a record field selection reaching field tag in the right-hand side concatenation 'ctrl.tag & ctrl.idx & ctrl.ofs & "00"' of the assignment to cache_o.addr. | ctrl.state = S_DOWNLOAD_RSP | FIELD_USE |
| line 235 | case alternative S_DOWNLOAD_RSP 233-250 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Base of a record field selection reaching field idx in the right-hand side concatenation 'ctrl.tag & ctrl.idx & ctrl.ofs & "00"' of the assignment to cache_o.addr. | ctrl.state = S_DOWNLOAD_RSP | FIELD_USE |
| line 235 | case alternative S_DOWNLOAD_RSP 233-250 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Base of a record field selection reaching field ofs in the right-hand side concatenation 'ctrl.tag & ctrl.idx & ctrl.ofs & "00"' of the assignment to cache_o.addr. | ctrl.state = S_DOWNLOAD_RSP | FIELD_USE |
| line 238 | case alternative S_DOWNLOAD_RSP 233-250 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Base of a record field selection reaching field tag in the right-hand side concatenation 'ctrl.tag & ctrl.idx & ctrl.ofs & "00"' of the assignment to bus_req_o.addr. | ctrl.state = S_DOWNLOAD_RSP | FIELD_USE |
| line 238 | case alternative S_DOWNLOAD_RSP 233-250 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Base of a record field selection reaching field idx in the right-hand side concatenation 'ctrl.tag & ctrl.idx & ctrl.ofs & "00"' of the assignment to bus_req_o.addr. | ctrl.state = S_DOWNLOAD_RSP | FIELD_USE |
| line 238 | case alternative S_DOWNLOAD_RSP 233-250 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Base of a record field selection reaching field ofs in the right-hand side concatenation 'ctrl.tag & ctrl.idx & ctrl.ofs & "00"' of the assignment to bus_req_o.addr. | ctrl.state = S_DOWNLOAD_RSP | FIELD_USE |
| line 242 | case alternative S_DOWNLOAD_RSP 233-250 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Base of a record field selection reaching field buf_err in the expression 'ctrl_nxt.buf_err <= ctrl.buf_err or bus_rsp_i.err;'. | ctrl.state = S_DOWNLOAD_RSP | FIELD_USE |
| line 244 | then branch 243-249 in if 243-250 in case alternative S_DOWNLOAD_RSP 233-250 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Base of a record field selection reaching field ofs as an argument in the expression 'std_ulogic_vector(unsigned(ctrl.ofs) + 1)'. | ctrl.state = S_DOWNLOAD_RSP AND bus_rsp_i.ack = '1' | FIELD_USE |
| line 245 | then branch 245-246 in if 245-249 in then branch 243-249 in if 243-250 in case alternative S_DOWNLOAD_RSP 233-250 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Base of a record field selection reaching field ofs in the condition 'if (and_reduce_f(ctrl.ofs) = '1') then'. | ctrl.state = S_DOWNLOAD_RSP AND bus_rsp_i.ack = '1' | FIELD_USE |
| line 254 | then branch 254-258 in if 254-261 in case alternative S_DOWNLOAD_DONE 252-261 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Base of a record field selection reaching field buf_err in the condition 'if (ctrl.buf_err = '1') then'. | ctrl.state = S_DOWNLOAD_DONE | FIELD_USE |

### ctrl.state

from validate

| Occurrence Lines | Context | Path | SITE Tagged |
| --- | --- | --- | --- |
| line 108 | declarative part 47-108 in architecture 44-294; The field's declaration is the signal declaration of the base; the record type is declared in this source. | - | DECL_FIELD |
| line 117 | then branch 116-124 in if 116-127 in process ctrl_engine_sync 114-128 in architecture 44-294; Target of a signal assignment inside a process; the record field written as the assignment target. | rstn_i = '0' | LHS_PROC |
| line 136 | process ctrl_engine_comb 133-268 in architecture 44-294; The whole right-hand side of a signal assignment inside a process; the right-hand side is exactly the field 'ctrl.state'. | - | DIRR_ASS |
| line 164 | case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Case expression of a case statement; the field is the case expression between 'case' and 'is'. | - | CASE_EXPR |

### ctrl.buf_req

from validate

| Occurrence Lines | Context | Path | SITE Tagged |
| --- | --- | --- | --- |
| line 108 | declarative part 47-108 in architecture 44-294; The field's declaration is the signal declaration of the base; the record type is declared in this source. | - | DECL_FIELD |
| line 118 | then branch 116-124 in if 116-127 in process ctrl_engine_sync 114-128 in architecture 44-294; Target of a signal assignment inside a process; the record field written as the assignment target. | rstn_i = '0' | LHS_PROC |
| line 137 | process ctrl_engine_comb 133-268 in architecture 44-294; An operand on the right-hand side joined by an operator ('or') in a signal assignment; the record field appears in the RHS expression. | - | RHS_OPERAND |
| line 170 | elsif branch 170-175 in if 168-176 in case alternative S_IDLE 166-176 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Element in the condition of an elsif (if statement); the field appears in the if/elsif condition. | ctrl.state = S_IDLE AND not ((host_req_i.fence = '1') or (ctrl.buf_sync = '1')) | IF_COND |

### ctrl.buf_sync

from validate

| Occurrence Lines | Context | Path | SITE Tagged |
| --- | --- | --- | --- |
| line 108 | declarative part 47-108 in architecture 44-294; The field's declaration is the signal declaration of the base; the record type is declared in this source. | - | DECL_FIELD |
| line 119 | then branch 116-124 in if 116-127 in process ctrl_engine_sync 114-128 in architecture 44-294; Target of a signal assignment inside a process; the record field written as the assignment target. | rstn_i = '0' | LHS_PROC |
| line 138 | process ctrl_engine_comb 133-268 in architecture 44-294; An operand on the right-hand side joined by an operator ('or') in a signal assignment; the record field appears in the RHS expression. | - | RHS_OPERAND |
| line 168 | then branch 168-169 in if 168-176 in case alternative S_IDLE 166-176 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Element in the condition of an if; the field appears in the if condition. | ctrl.state = S_IDLE | IF_COND |

### ctrl.buf_err

from validate

| Occurrence Lines | Context | Path | SITE Tagged |
| --- | --- | --- | --- |
| line 108 | declarative part 47-108 in architecture 44-294; The field's declaration is the signal declaration of the base; the record type is declared in this source. | - | DECL_FIELD |
| line 120 | then branch 116-124 in if 116-127 in process ctrl_engine_sync 114-128 in architecture 44-294; Target of a signal assignment inside a process; the record field written as the assignment target. | rstn_i = '0' | LHS_PROC |
| line 139 | process ctrl_engine_comb 133-268 in architecture 44-294; The whole right-hand side of a signal assignment inside a process; the field appears alone on the RHS. | - | DIRR_ASS |
| line 242 | case alternative S_DOWNLOAD_RSP 233-250 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; An operand on the right-hand side joined by an operator ('or') in a signal assignment; the record field appears in the RHS expression. | ctrl.state = S_DOWNLOAD_RSP | RHS_OPERAND |
| line 254 | then branch 254-258 in if 254-261 in case alternative S_DOWNLOAD_DONE 252-261 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Element in the condition of an if; the field appears in the if condition. | ctrl.state = S_DOWNLOAD_DONE | IF_COND |

### ctrl.buf_dir

from validate

| Occurrence Lines | Context | Path | SITE Tagged |
| --- | --- | --- | --- |
| line 108 | declarative part 47-108 in architecture 44-294; The field's declaration is the signal declaration of the base; the record type is declared in this source. | - | DECL_FIELD |
| line 121 | then branch 116-124 in if 116-127 in process ctrl_engine_sync 114-128 in architecture 44-294; Target of a signal assignment inside a process; the record field written as the assignment target. | rstn_i = '0' | LHS_PROC |
| line 186 | then branch 186-188 in if 186-205 in case alternative S_LOOKUP 178-205 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Element in the condition of an if; the field appears in the if condition. | ctrl.state = S_LOOKUP | IF_COND |

### ctrl.tag

from validate

| Occurrence Lines | Context | Path | SITE Tagged |
| --- | --- | --- | --- |
| line 108 | declarative part 47-108 in architecture 44-294; Declaration of the base signal ctrl; this records the field's declaration (record type declared in this source). | - | DECL_FIELD |
| line 122 | then branch 116-124 in if 116-127 in process ctrl_engine_sync 114-128 in architecture 44-294; Sequential signal assignment target: left-hand side of <= inside a process, assigning to the field ctrl.tag. | rstn_i = '0' | LHS_PROC |
| line 141 | process ctrl_engine_comb 133-268 in architecture 44-294; Sequential signal assignment whole right-hand side: the RHS is the field ctrl.tag alone. | - | DIRR_ASS |
| line 225 | case alternative S_DOWNLOAD_REQ 223-231 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Sequential signal assignment right-hand side operand: the field ctrl.tag is an operand joined by &. | ctrl.state = S_DOWNLOAD_REQ | RHS_OPERAND |
| line 227 | case alternative S_DOWNLOAD_REQ 223-231 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Sequential signal assignment right-hand side operand: the field ctrl.tag is an operand joined by &. | ctrl.state = S_DOWNLOAD_REQ | RHS_OPERAND |
| line 235 | case alternative S_DOWNLOAD_RSP 233-250 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Sequential signal assignment right-hand side operand: the field ctrl.tag is an operand joined by &. | ctrl.state = S_DOWNLOAD_RSP | RHS_OPERAND |
| line 238 | case alternative S_DOWNLOAD_RSP 233-250 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Sequential signal assignment right-hand side operand: the field ctrl.tag is an operand joined by &. | ctrl.state = S_DOWNLOAD_RSP | RHS_OPERAND |

### ctrl.idx

from validate

| Occurrence Lines | Context | Path | SITE Tagged |
| --- | --- | --- | --- |
| line 108 | declarative part 47-108 in architecture 44-294; Declaration of the base signal ctrl; this records the field's declaration (record type declared in this source). | - | DECL_FIELD |
| line 123 | then branch 116-124 in if 116-127 in process ctrl_engine_sync 114-128 in architecture 44-294; Sequential signal assignment target: left-hand side of <= inside a process, assigning to the field ctrl.idx. | rstn_i = '0' | LHS_PROC |
| line 142 | process ctrl_engine_comb 133-268 in architecture 44-294; Sequential signal assignment whole right-hand side: the RHS is the field ctrl.idx alone. | - | DIRR_ASS |
| line 225 | case alternative S_DOWNLOAD_REQ 223-231 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Sequential signal assignment right-hand side operand: the field ctrl.idx is an operand joined by &. | ctrl.state = S_DOWNLOAD_REQ | RHS_OPERAND |
| line 227 | case alternative S_DOWNLOAD_REQ 223-231 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Sequential signal assignment right-hand side operand: the field ctrl.idx is an operand joined by &. | ctrl.state = S_DOWNLOAD_REQ | RHS_OPERAND |
| line 235 | case alternative S_DOWNLOAD_RSP 233-250 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Sequential signal assignment right-hand side operand: the field ctrl.idx is an operand joined by &. | ctrl.state = S_DOWNLOAD_RSP | RHS_OPERAND |
| line 238 | case alternative S_DOWNLOAD_RSP 233-250 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Sequential signal assignment right-hand side operand: the field ctrl.idx is an operand joined by &. | ctrl.state = S_DOWNLOAD_RSP | RHS_OPERAND |

### ctrl.ofs

from validate

| Occurrence Lines | Context | Path | SITE Tagged |
| --- | --- | --- | --- |
| line 108 | declarative part 47-108 in architecture 44-294; Declaration of the base signal ctrl; this records the field's declaration (record type declared in this source). | - | DECL_FIELD |
| line 124 | then branch 116-124 in if 116-127 in process ctrl_engine_sync 114-128 in architecture 44-294; Sequential signal assignment target: left-hand side of <= inside a process, assigning to the field ctrl.ofs. | rstn_i = '0' | LHS_PROC |
| line 143 | process ctrl_engine_comb 133-268 in architecture 44-294; Sequential signal assignment whole right-hand side: the RHS is the field ctrl.ofs alone. | - | DIRR_ASS |
| line 225 | case alternative S_DOWNLOAD_REQ 223-231 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Sequential signal assignment right-hand side operand: the field ctrl.ofs is an operand joined by &. | ctrl.state = S_DOWNLOAD_REQ | RHS_OPERAND |
| line 227 | case alternative S_DOWNLOAD_REQ 223-231 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Sequential signal assignment right-hand side operand: the field ctrl.ofs is an operand joined by &. | ctrl.state = S_DOWNLOAD_REQ | RHS_OPERAND |
| line 235 | case alternative S_DOWNLOAD_RSP 233-250 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Sequential signal assignment right-hand side operand: the field ctrl.ofs is an operand joined by &. | ctrl.state = S_DOWNLOAD_RSP | RHS_OPERAND |
| line 238 | case alternative S_DOWNLOAD_RSP 233-250 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Sequential signal assignment right-hand side operand: the field ctrl.ofs is an operand joined by &. | ctrl.state = S_DOWNLOAD_RSP | RHS_OPERAND |
| line 244 | then branch 243-249 in if 243-250 in case alternative S_DOWNLOAD_RSP 233-250 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Sequential signal assignment right-hand side operand: ctrl.ofs appears inside a conversion and is part of an expression (unsigned(ctrl.ofs) + 1). | ctrl.state = S_DOWNLOAD_RSP AND bus_rsp_i.ack = '1' | RHS_OPERAND |
| line 245 | then branch 245-246 in if 245-249 in then branch 243-249 in if 243-250 in case alternative S_DOWNLOAD_RSP 233-250 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; If condition: the element appears inside the condition (and_reduce_f(ctrl.ofs) = '1') of an if statement inside a process. | ctrl.state = S_DOWNLOAD_RSP AND bus_rsp_i.ack = '1' | IF_COND |

### ctrl_nxt

from validate

| Occurrence Lines | Context | Path | SITE Tagged |
| --- | --- | --- | --- |
| line 108 | declarative part 47-108 in architecture 44-294; Declaration of the signal ctrl_nxt of type ctrl_t. | - | DECL_SIGNAL |
| line 126 | elsif branch 125-126 in if 116-127 in process ctrl_engine_sync 114-128 in architecture 44-294; Sequential signal assignment whole right-hand side: ctrl_nxt is the RHS of a signal assignment inside a process. | not (rstn_i = '0') AND rising_edge(clk_i) | DIRR_ASS |
| line 136 | process ctrl_engine_comb 133-268 in architecture 44-294; FIELD_USE: base ctrl_nxt used to reach field state. | - | FIELD_USE |
| line 137 | process ctrl_engine_comb 133-268 in architecture 44-294; FIELD_USE: base ctrl_nxt used to reach field buf_req. | - | FIELD_USE |
| line 138 | process ctrl_engine_comb 133-268 in architecture 44-294; FIELD_USE: base ctrl_nxt used to reach field buf_sync. | - | FIELD_USE |
| line 139 | process ctrl_engine_comb 133-268 in architecture 44-294; FIELD_USE: base ctrl_nxt used to reach field buf_err. | - | FIELD_USE |
| line 140 | process ctrl_engine_comb 133-268 in architecture 44-294; FIELD_USE: base ctrl_nxt used to reach field buf_dir. | - | FIELD_USE |
| line 141 | process ctrl_engine_comb 133-268 in architecture 44-294; FIELD_USE: base ctrl_nxt used to reach field tag. | - | FIELD_USE |
| line 142 | process ctrl_engine_comb 133-268 in architecture 44-294; FIELD_USE: base ctrl_nxt used to reach field idx. | - | FIELD_USE |
| line 143 | process ctrl_engine_comb 133-268 in architecture 44-294; FIELD_USE: base ctrl_nxt used to reach field ofs. | - | FIELD_USE |
| line 169 | then branch 168-169 in if 168-176 in case alternative S_IDLE 166-176 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; FIELD_USE: base ctrl_nxt used to reach field state. | ctrl.state = S_IDLE AND (host_req_i.fence = '1') or (ctrl.buf_sync = '1') | FIELD_USE |
| line 173 | then branch 171-173 in if 171-174 in elsif branch 170-175 in if 168-176 in case alternative S_IDLE 166-176 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; FIELD_USE: base ctrl_nxt used to reach field buf_dir. | ctrl.state = S_IDLE AND not ((host_req_i.fence = '1') or (ctrl.buf_sync = '1')) AND (host_req_i.stb = '1') or (ctrl.buf_req = '1') AND (unsigned(host_req_i.addr(31 downto 28)) >= unsigned(UC_BEGIN)) or (host_req_i.amo = '1') or (host_req_i.debug = '1') | FIELD_USE |
| line 175 | elsif branch 170-175 in if 168-176 in case alternative S_IDLE 166-176 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; FIELD_USE: base ctrl_nxt used to reach field state. | ctrl.state = S_IDLE AND not ((host_req_i.fence = '1') or (ctrl.buf_sync = '1')) AND (host_req_i.stb = '1') or (ctrl.buf_req = '1') | FIELD_USE |
| line 180 | case alternative S_LOOKUP 178-205 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; FIELD_USE: base ctrl_nxt used to reach field tag. | ctrl.state = S_LOOKUP | FIELD_USE |
| line 181 | case alternative S_LOOKUP 178-205 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; FIELD_USE: base ctrl_nxt used to reach field idx. | ctrl.state = S_LOOKUP | FIELD_USE |
| line 182 | case alternative S_LOOKUP 178-205 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; FIELD_USE: base ctrl_nxt used to reach field ofs. | ctrl.state = S_LOOKUP | FIELD_USE |
| line 183 | case alternative S_LOOKUP 178-205 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; FIELD_USE: base ctrl_nxt used to reach field buf_err. | ctrl.state = S_LOOKUP | FIELD_USE |
| line 184 | case alternative S_LOOKUP 178-205 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; FIELD_USE: base ctrl_nxt used to reach field buf_req. | ctrl.state = S_LOOKUP | FIELD_USE |
| line 188 | then branch 186-188 in if 186-205 in case alternative S_LOOKUP 178-205 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; FIELD_USE: base ctrl_nxt used to reach field state. | ctrl.state = S_LOOKUP AND ctrl.buf_dir = '1' | FIELD_USE |
| line 192 | then branch 190-192 in if 190-197 in elsif branch 189-197 in if 186-205 in case alternative S_LOOKUP 178-205 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; FIELD_USE: base ctrl_nxt used to reach field state. | ctrl.state = S_LOOKUP AND not (ctrl.buf_dir = '1') AND cache_i.sta_hit = '1' AND (host_req_i.rw = '0') or (READ_ONLY = true) | FIELD_USE |
| line 196 | else branch 193-196 in if 190-197 in elsif branch 189-197 in if 186-205 in case alternative S_LOOKUP 178-205 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; FIELD_USE: base ctrl_nxt used to reach field state. | ctrl.state = S_LOOKUP AND not (ctrl.buf_dir = '1') AND cache_i.sta_hit = '1' AND not ((host_req_i.rw = '0') or (READ_ONLY = true)) | FIELD_USE |
| line 200 | then branch 199-200 in if 199-204 in else branch 198-204 in if 186-205 in case alternative S_LOOKUP 178-205 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; FIELD_USE: base ctrl_nxt used to reach field state. | ctrl.state = S_LOOKUP AND not (ctrl.buf_dir = '1') AND not (cache_i.sta_hit = '1') AND (host_req_i.rw = '0') or (READ_ONLY = true) | FIELD_USE |
| line 203 | else branch 201-203 in if 199-204 in else branch 198-204 in if 186-205 in case alternative S_LOOKUP 178-205 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; FIELD_USE: base ctrl_nxt used to reach field state. | ctrl.state = S_LOOKUP AND not (ctrl.buf_dir = '1') AND not (cache_i.sta_hit = '1') AND not ((host_req_i.rw = '0') or (READ_ONLY = true)) | FIELD_USE |
| line 211 | then branch 210-211 in if 210-212 in case alternative S_DIRECT_RSP 207-212 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; FIELD_USE: base ctrl_nxt used to reach field state. | ctrl.state = S_DIRECT_RSP AND bus_rsp_i.ack = '1' | FIELD_USE |
| line 220 | case alternative S_CLEAR 214-221 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; FIELD_USE: base ctrl_nxt used to reach field buf_sync. | ctrl.state = S_CLEAR | FIELD_USE |
| line 221 | case alternative S_CLEAR 214-221 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; FIELD_USE: base ctrl_nxt used to reach field state. | ctrl.state = S_CLEAR | FIELD_USE |
| line 231 | case alternative S_DOWNLOAD_REQ 223-231 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; FIELD_USE: base ctrl_nxt used to reach field state. | ctrl.state = S_DOWNLOAD_REQ | FIELD_USE |
| line 242 | case alternative S_DOWNLOAD_RSP 233-250 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; FIELD_USE: base ctrl_nxt used to reach field buf_err. | ctrl.state = S_DOWNLOAD_RSP | FIELD_USE |
| line 244 | then branch 243-249 in if 243-250 in case alternative S_DOWNLOAD_RSP 233-250 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; FIELD_USE: base ctrl_nxt used to reach field ofs. | ctrl.state = S_DOWNLOAD_RSP AND bus_rsp_i.ack = '1' | FIELD_USE |
| line 246 | then branch 245-246 in if 245-249 in then branch 243-249 in if 243-250 in case alternative S_DOWNLOAD_RSP 233-250 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; FIELD_USE: base ctrl_nxt used to reach field state. | ctrl.state = S_DOWNLOAD_RSP AND bus_rsp_i.ack = '1' AND and_reduce_f(ctrl.ofs) = '1' | FIELD_USE |
| line 248 | else branch 247-248 in if 245-249 in then branch 243-249 in if 243-250 in case alternative S_DOWNLOAD_RSP 233-250 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; FIELD_USE: base ctrl_nxt used to reach field state. | ctrl.state = S_DOWNLOAD_RSP AND bus_rsp_i.ack = '1' AND not (and_reduce_f(ctrl.ofs) = '1') | FIELD_USE |
| line 258 | then branch 254-258 in if 254-261 in case alternative S_DOWNLOAD_DONE 252-261 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; FIELD_USE: base ctrl_nxt used to reach field state. | ctrl.state = S_DOWNLOAD_DONE AND ctrl.buf_err = '1' | FIELD_USE |
| line 260 | else branch 259-260 in if 254-261 in case alternative S_DOWNLOAD_DONE 252-261 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; FIELD_USE: base ctrl_nxt used to reach field state. | ctrl.state = S_DOWNLOAD_DONE AND not (ctrl.buf_err = '1') | FIELD_USE |
| line 265 | case alternative others 263-265 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; FIELD_USE: base ctrl_nxt used to reach field state. | not (ctrl.state in {S_IDLE, S_LOOKUP, S_DIRECT_RSP, S_CLEAR, S_DOWNLOAD_REQ, S_DOWNLOAD_RSP, S_DOWNLOAD_DONE}) | FIELD_USE |

### ctrl_nxt.state

from validate

| Occurrence Lines | Context | Path | SITE Tagged |
| --- | --- | --- | --- |
| line 108 | declarative part 47-108 in architecture 44-294; Declaration of the base signal ctrl_nxt; this records the field's declaration (record type declared in this source). | - | DECL_FIELD |
| line 136 | process ctrl_engine_comb 133-268 in architecture 44-294; Sequential signal assignment target: left-hand side of <= inside a process, assigning to ctrl_nxt.state. | - | LHS_PROC |
| line 169 | then branch 168-169 in if 168-176 in case alternative S_IDLE 166-176 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Sequential signal assignment target: left-hand side of <= inside a process, assigning to ctrl_nxt.state. | ctrl.state = S_IDLE AND (host_req_i.fence = '1') or (ctrl.buf_sync = '1') | LHS_PROC |
| line 175 | elsif branch 170-175 in if 168-176 in case alternative S_IDLE 166-176 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Sequential signal assignment target: left-hand side of <= inside a process, assigning to ctrl_nxt.state. | ctrl.state = S_IDLE AND not ((host_req_i.fence = '1') or (ctrl.buf_sync = '1')) AND (host_req_i.stb = '1') or (ctrl.buf_req = '1') | LHS_PROC |
| line 188 | then branch 186-188 in if 186-205 in case alternative S_LOOKUP 178-205 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Sequential signal assignment target: left-hand side of <= inside a process, assigning to ctrl_nxt.state. | ctrl.state = S_LOOKUP AND ctrl.buf_dir = '1' | LHS_PROC |
| line 192 | then branch 190-192 in if 190-197 in elsif branch 189-197 in if 186-205 in case alternative S_LOOKUP 178-205 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Sequential signal assignment target: left-hand side of <= inside a process, assigning to ctrl_nxt.state. | ctrl.state = S_LOOKUP AND not (ctrl.buf_dir = '1') AND cache_i.sta_hit = '1' AND (host_req_i.rw = '0') or (READ_ONLY = true) | LHS_PROC |
| line 196 | else branch 193-196 in if 190-197 in elsif branch 189-197 in if 186-205 in case alternative S_LOOKUP 178-205 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Sequential signal assignment target: left-hand side of <= inside a process, assigning to ctrl_nxt.state. | ctrl.state = S_LOOKUP AND not (ctrl.buf_dir = '1') AND cache_i.sta_hit = '1' AND not ((host_req_i.rw = '0') or (READ_ONLY = true)) | LHS_PROC |
| line 200 | then branch 199-200 in if 199-204 in else branch 198-204 in if 186-205 in case alternative S_LOOKUP 178-205 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Sequential signal assignment target: left-hand side of <= inside a process, assigning to ctrl_nxt.state. | ctrl.state = S_LOOKUP AND not (ctrl.buf_dir = '1') AND not (cache_i.sta_hit = '1') AND (host_req_i.rw = '0') or (READ_ONLY = true) | LHS_PROC |
| line 203 | else branch 201-203 in if 199-204 in else branch 198-204 in if 186-205 in case alternative S_LOOKUP 178-205 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Sequential signal assignment target: left-hand side of <= inside a process, assigning to ctrl_nxt.state. | ctrl.state = S_LOOKUP AND not (ctrl.buf_dir = '1') AND not (cache_i.sta_hit = '1') AND not ((host_req_i.rw = '0') or (READ_ONLY = true)) | LHS_PROC |
| line 211 | then branch 210-211 in if 210-212 in case alternative S_DIRECT_RSP 207-212 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Sequential signal assignment target: left-hand side of <= inside a process, assigning to ctrl_nxt.state. | ctrl.state = S_DIRECT_RSP AND bus_rsp_i.ack = '1' | LHS_PROC |
| line 221 | case alternative S_CLEAR 214-221 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Sequential signal assignment target: left-hand side of <= inside a process, assigning to ctrl_nxt.state. | ctrl.state = S_CLEAR | LHS_PROC |
| line 231 | case alternative S_DOWNLOAD_REQ 223-231 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Sequential signal assignment target: left-hand side of <= inside a process, assigning to ctrl_nxt.state. | ctrl.state = S_DOWNLOAD_REQ | LHS_PROC |
| line 246 | then branch 245-246 in if 245-249 in then branch 243-249 in if 243-250 in case alternative S_DOWNLOAD_RSP 233-250 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Sequential signal assignment target: left-hand side of <= inside a process, assigning to ctrl_nxt.state. | ctrl.state = S_DOWNLOAD_RSP AND bus_rsp_i.ack = '1' AND and_reduce_f(ctrl.ofs) = '1' | LHS_PROC |
| line 248 | else branch 247-248 in if 245-249 in then branch 243-249 in if 243-250 in case alternative S_DOWNLOAD_RSP 233-250 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Sequential signal assignment target: left-hand side of <= inside a process, assigning to ctrl_nxt.state. | ctrl.state = S_DOWNLOAD_RSP AND bus_rsp_i.ack = '1' AND not (and_reduce_f(ctrl.ofs) = '1') | LHS_PROC |
| line 258 | then branch 254-258 in if 254-261 in case alternative S_DOWNLOAD_DONE 252-261 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Sequential signal assignment target: left-hand side of <= inside a process, assigning to ctrl_nxt.state. | ctrl.state = S_DOWNLOAD_DONE AND ctrl.buf_err = '1' | LHS_PROC |
| line 260 | else branch 259-260 in if 254-261 in case alternative S_DOWNLOAD_DONE 252-261 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Sequential signal assignment target: left-hand side of <= inside a process, assigning to ctrl_nxt.state. | ctrl.state = S_DOWNLOAD_DONE AND not (ctrl.buf_err = '1') | LHS_PROC |
| line 265 | case alternative others 263-265 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Sequential signal assignment target: left-hand side of <= inside a process, assigning to ctrl_nxt.state. | not (ctrl.state in {S_IDLE, S_LOOKUP, S_DIRECT_RSP, S_CLEAR, S_DOWNLOAD_REQ, S_DOWNLOAD_RSP, S_DOWNLOAD_DONE}) | LHS_PROC |

### ctrl_nxt.buf_req

from validate

| Occurrence Lines | Context | Path | SITE Tagged |
| --- | --- | --- | --- |
| line 108 | declarative part 47-108 in architecture 44-294; Declaration of the base signal ctrl_nxt; this records the field's declaration (record type declared in this source). | - | DECL_FIELD |
| line 137 | process ctrl_engine_comb 133-268 in architecture 44-294; Sequential signal assignment target: left-hand side of <= inside a process, assigning to ctrl_nxt.buf_req. | - | LHS_PROC |
| line 184 | case alternative S_LOOKUP 178-205 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Sequential signal assignment target: left-hand side of <= inside a process, assigning to ctrl_nxt.buf_req. | ctrl.state = S_LOOKUP | LHS_PROC |

### ctrl_nxt.buf_sync

from validate

| Occurrence Lines | Context | Path | SITE Tagged |
| --- | --- | --- | --- |
| line 108 | declarative part 47-108 in architecture 44-294; Declaration of the base signal ctrl_nxt; this records the field's declaration (record type declared in this source). | - | DECL_FIELD |
| line 138 | process ctrl_engine_comb 133-268 in architecture 44-294; Sequential signal assignment target: left-hand side of <= inside a process, assigning to ctrl_nxt.buf_sync. | - | LHS_PROC |
| line 220 | case alternative S_CLEAR 214-221 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Sequential signal assignment target: left-hand side of <= inside a process, assigning to ctrl_nxt.buf_sync. | ctrl.state = S_CLEAR | LHS_PROC |

### ctrl_nxt.buf_err

from validate

| Occurrence Lines | Context | Path | SITE Tagged |
| --- | --- | --- | --- |
| line 108 | declarative part 47-108 in architecture 44-294; Declaration of the base signal ctrl_nxt; this records the field's declaration (record type declared in this source). | - | DECL_FIELD |
| line 139 | process ctrl_engine_comb 133-268 in architecture 44-294; Sequential signal assignment target: left-hand side of <= inside a process, assigning to ctrl_nxt.buf_err. | - | LHS_PROC |
| line 183 | case alternative S_LOOKUP 178-205 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Sequential signal assignment target: left-hand side of <= inside a process, assigning to ctrl_nxt.buf_err. | ctrl.state = S_LOOKUP | LHS_PROC |
| line 242 | case alternative S_DOWNLOAD_RSP 233-250 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Sequential signal assignment target: left-hand side of <= inside a process, assigning to ctrl_nxt.buf_err. | ctrl.state = S_DOWNLOAD_RSP | LHS_PROC |

### ctrl_nxt.buf_dir

from validate

| Occurrence Lines | Context | Path | SITE Tagged |
| --- | --- | --- | --- |
| line 108 | declarative part 47-108 in architecture 44-294; Declaration: this is the signal declaration of the base ctrl_nxt that defines the field buf_dir; the record type ctrl_t is declared in this source. | - | DECL_FIELD |
| line 140 | process ctrl_engine_comb 133-268 in architecture 44-294; Sequential signal assignment: the field is the target on the left of <= in a signal assignment inside process ctrl_engine_comb. | - | LHS_PROC |
| line 173 | then branch 171-173 in if 171-174 in elsif branch 170-175 in if 168-176 in case alternative S_IDLE 166-176 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Sequential signal assignment: the field is the target on the left of <= in a signal assignment inside process ctrl_engine_comb. | ctrl.state = S_IDLE AND not ((host_req_i.fence = '1') or (ctrl.buf_sync = '1')) AND (host_req_i.stb = '1') or (ctrl.buf_req = '1') AND (unsigned(host_req_i.addr(31 downto 28)) >= unsigned(UC_BEGIN)) or (host_req_i.amo = '1') or (host_req_i.debug = '1') | LHS_PROC |

### ctrl_nxt.tag

from validate

| Occurrence Lines | Context | Path | SITE Tagged |
| --- | --- | --- | --- |
| line 108 | declarative part 47-108 in architecture 44-294; Declaration: this is the signal declaration of the base ctrl_nxt that defines the field tag; the record type ctrl_t is declared in this source. | - | DECL_FIELD |
| line 141 | process ctrl_engine_comb 133-268 in architecture 44-294; Sequential signal assignment: the field is the target on the left of <= in a signal assignment inside process ctrl_engine_comb. | - | LHS_PROC |
| line 180 | case alternative S_LOOKUP 178-205 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Sequential signal assignment: the field is the target on the left of <= in a signal assignment inside process ctrl_engine_comb. | ctrl.state = S_LOOKUP | LHS_PROC |

### ctrl_nxt.idx

from validate

| Occurrence Lines | Context | Path | SITE Tagged |
| --- | --- | --- | --- |
| line 108 | declarative part 47-108 in architecture 44-294; Declaration: this is the signal declaration of the base ctrl_nxt that defines the field idx; the record type ctrl_t is declared in this source. | - | DECL_FIELD |
| line 142 | process ctrl_engine_comb 133-268 in architecture 44-294; Sequential signal assignment: the field is the target on the left of <= in a signal assignment inside process ctrl_engine_comb. | - | LHS_PROC |
| line 181 | case alternative S_LOOKUP 178-205 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Sequential signal assignment: the field is the target on the left of <= in a signal assignment inside process ctrl_engine_comb. | ctrl.state = S_LOOKUP | LHS_PROC |

### ctrl_nxt.ofs

from validate

| Occurrence Lines | Context | Path | SITE Tagged |
| --- | --- | --- | --- |
| line 108 | declarative part 47-108 in architecture 44-294; Declaration: this is the signal declaration of the base ctrl_nxt that defines the field ofs; the record type ctrl_t is declared in this source. | - | DECL_FIELD |
| line 143 | process ctrl_engine_comb 133-268 in architecture 44-294; Sequential signal assignment: the field is the target on the left of <= in a signal assignment inside process ctrl_engine_comb. | - | LHS_PROC |
| line 182 | case alternative S_LOOKUP 178-205 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Sequential signal assignment: the field is the target on the left of <= in a signal assignment inside process ctrl_engine_comb. | ctrl.state = S_LOOKUP | LHS_PROC |
| line 244 | then branch 243-249 in if 243-250 in case alternative S_DOWNLOAD_RSP 233-250 in case ctrl.state 164-267 in process ctrl_engine_comb 133-268 in architecture 44-294; Sequential signal assignment: the field is the target on the left of <= in a signal assignment inside process ctrl_engine_comb. | ctrl.state = S_DOWNLOAD_RSP AND bus_rsp_i.ack = '1' | LHS_PROC |

## Entity neorv32_cache_memory

### rstn_i

from validate

| Occurrence Lines | Context | Path | SITE Tagged |
| --- | --- | --- | --- |
| line 321 | port clause 319-333 in entity 314-334; Declared port in the entity's port clause. | - | DECL_PORT |
| line 374 | process status_memory 374-389 in architecture 336-433; Named in the sensitivity list of the process statement status_memory. | - | PROCESS_TRIG |
| line 376 | then branch 376-378 in if 376-388 in process status_memory 374-389 in architecture 336-433; Used in the condition of an if statement inside a process. | - | IF_COND |

### clk_i

from validate

| Occurrence Lines | Context | Path | SITE Tagged |
| --- | --- | --- | --- |
| line 322 | port clause 319-333 in entity 314-334; Declared port in the entity's port clause. | - | DECL_PORT |
| line 374 | process status_memory 374-389 in architecture 336-433; Named in the sensitivity list of the process statement status_memory. | - | PROCESS_TRIG |
| line 379 | elsif branch 379-387 in if 376-388 in process status_memory 374-389 in architecture 336-433; Argument of rising_edge(...) in an elsif condition inside a process. | not (rstn_i = '0') | EDGE_CHECK |
| line 394 | process tag_memory 394-402 in architecture 336-433; Named in the sensitivity list of the process statement tag_memory. | - | PROCESS_TRIG |
| line 396 | then branch 396-400 in if 396-401 in process tag_memory 394-402 in architecture 336-433; Argument of rising_edge(...) in the if condition inside the tag_memory process. | - | EDGE_CHECK |
| line 410 | process data_memory 410-430 in architecture 336-433; Named in the sensitivity list of the process statement data_memory. | - | PROCESS_TRIG |
| line 412 | then branch 412-428 in if 412-429 in process data_memory 410-430 in architecture 336-433; Argument of rising_edge(...) in the if condition inside the data_memory process. | - | EDGE_CHECK |

### clr_i

from validate

| Occurrence Lines | Context | Path | SITE Tagged |
| --- | --- | --- | --- |
| line 324 | port clause 319-333 in entity 314-334; Declared port in the entity's port clause. | - | DECL_PORT |
| line 380 | then branch 380-381 in if 380-386 in elsif branch 379-387 in if 376-388 in process status_memory 374-389 in architecture 336-433; Used in the condition of an if statement inside a process. | not (rstn_i = '0') AND rising_edge(clk_i) | IF_COND |

### inv_i

from validate

| Occurrence Lines | Context | Path | SITE Tagged |
| --- | --- | --- | --- |
| line 325 | port clause 319-333 in entity 314-334; Declared port in the entity's port clause. | - | DECL_PORT |
| line 382 | elsif branch 382-383 in if 380-386 in elsif branch 379-387 in if 376-388 in process status_memory 374-389 in architecture 336-433; Used in the condition of an elsif inside a process. | not (rstn_i = '0') AND rising_edge(clk_i) AND not (clr_i = '1') | IF_COND |

### new_i

from validate

| Occurrence Lines | Context | Path | SITE Tagged |
| --- | --- | --- | --- |
| line 326 | port clause 319-333 in entity 314-334; Declared port in the entity's port clause. | - | DECL_PORT |
| line 384 | elsif branch 384-385 in if 380-386 in elsif branch 379-387 in if 376-388 in process status_memory 374-389 in architecture 336-433; Used in the condition of an elsif inside a process. | not (rstn_i = '0') AND rising_edge(clk_i) AND not (clr_i = '1') AND not (inv_i = '1') | IF_COND |
| line 397 | then branch 397-398 in if 397-399 in then branch 396-400 in if 396-401 in process tag_memory 394-402 in architecture 336-433; Used in the condition of an if statement inside the tag_memory process. | rising_edge(clk_i) | IF_COND |

### hit_o

from validate

| Occurrence Lines | Context | Path | SITE Tagged |
| --- | --- | --- | --- |
| line 327 | port clause 319-333 in entity 314-334; Declared port in the entity's port clause. | - | DECL_PORT |
| line 405 | when else 405-405 in architecture 336-433; Target (left-hand side) of a concurrent conditional signal assignment (when-else). | - | LHS_CONC |

### addr_i

from validate

| Occurrence Lines | Context | Path | SITE Tagged |
| --- | --- | --- | --- |
| line 329 | port clause 319-333 in entity 314-334; Declared port in the entity's port clause. | - | DECL_PORT |
| line 366 | architecture 336-433; Part-select of addr_i used as the whole right-hand side (bits 31 downto 31-(tag_size_c-1)). | - | PART_SELECT |
| line 367 | architecture 336-433; Part-select of addr_i used as the whole right-hand side (bits 31-tag_size_c downto 2+offset_size_c). | - | PART_SELECT |
| line 368 | architecture 336-433; Part-select of addr_i used as the whole right-hand side (bits 2+(offset_size_c-1) downto 2). | - | PART_SELECT |

### we_i

from validate

| Occurrence Lines | Context | Path | SITE Tagged |
| --- | --- | --- | --- |
| line 330 | port clause 319-333 in entity 314-334; Declared port in the entity's port clause. | - | DECL_PORT |
| line 413 | then branch 413-414 in if 413-415 in then branch 412-428 in if 412-429 in process data_memory 410-430 in architecture 336-433; Used in an if condition inside a process; the vector is indexed at (0). | rising_edge(clk_i) | IF_COND, INDEXED_NAME |
| line 416 | then branch 416-417 in if 416-418 in then branch 412-428 in if 412-429 in process data_memory 410-430 in architecture 336-433; Used in an if condition inside a process; the vector is indexed at (1). | rising_edge(clk_i) | IF_COND, INDEXED_NAME |
| line 419 | then branch 419-420 in if 419-421 in then branch 412-428 in if 412-429 in process data_memory 410-430 in architecture 336-433; Used in an if condition inside a process; the vector is indexed at (2). | rising_edge(clk_i) | IF_COND, INDEXED_NAME |
| line 422 | then branch 422-423 in if 422-424 in then branch 412-428 in if 412-429 in process data_memory 410-430 in architecture 336-433; Used in an if condition inside a process; the vector is indexed at (3). | rising_edge(clk_i) | IF_COND, INDEXED_NAME |

### wdata_i

from validate

| Occurrence Lines | Context | Path | SITE Tagged |
| --- | --- | --- | --- |
| line 331 | port clause 319-333 in entity 314-334; Declared port in the entity's port clause. | - | DECL_PORT |
| line 414 | then branch 413-414 in if 413-415 in then branch 412-428 in if 412-429 in process data_memory 410-430 in architecture 336-433; Part-select of wdata_i (7 downto 0) used as the whole right-hand side of a sequential signal assignment. | rising_edge(clk_i) AND we_i(0) = '1' | PART_SELECT |
| line 417 | then branch 416-417 in if 416-418 in then branch 412-428 in if 412-429 in process data_memory 410-430 in architecture 336-433; Part-select of wdata_i (15 downto 8) used as the whole right-hand side of a sequential signal assignment. | rising_edge(clk_i) AND we_i(1) = '1' | PART_SELECT |
| line 420 | then branch 419-420 in if 419-421 in then branch 412-428 in if 412-429 in process data_memory 410-430 in architecture 336-433; Part-select of wdata_i (23 downto 16) used as the whole right-hand side of a sequential signal assignment. | rising_edge(clk_i) AND we_i(2) = '1' | PART_SELECT |
| line 423 | then branch 422-423 in if 422-424 in then branch 412-428 in if 412-429 in process data_memory 410-430 in architecture 336-433; Part-select of wdata_i (31 downto 24) used as the whole right-hand side of a sequential signal assignment. | rising_edge(clk_i) AND we_i(3) = '1' | PART_SELECT |

### rdata_o

from validate

| Occurrence Lines | Context | Path | SITE Tagged |
| --- | --- | --- | --- |
| line 332 | port clause 319-333 in entity 314-334; Declared port in the entity's port clause. | - | DECL_PORT |
| line 425 | then branch 412-428 in if 412-429 in process data_memory 410-430 in architecture 336-433; Target slice (7 downto 0) of a sequential signal assignment inside a process. | rising_edge(clk_i) | LHS_PROC, PART_SELECT |
| line 426 | then branch 412-428 in if 412-429 in process data_memory 410-430 in architecture 336-433; Target slice (15 downto 8) of a sequential signal assignment inside a process. | rising_edge(clk_i) | LHS_PROC, PART_SELECT |
| line 427 | then branch 412-428 in if 412-429 in process data_memory 410-430 in architecture 336-433; Target slice (23 downto 16) of a sequential signal assignment inside a process. | rising_edge(clk_i) | LHS_PROC, PART_SELECT |
| line 428 | then branch 412-428 in if 412-429 in process data_memory 410-430 in architecture 336-433; Target slice (31 downto 24) of a sequential signal assignment inside a process. | rising_edge(clk_i) | LHS_PROC, PART_SELECT |

### valid_mem

from validate

| Occurrence Lines | Context | Path | SITE Tagged |
| --- | --- | --- | --- |
| line 344 | declarative part 339-360 in architecture 336-433; Declared signal in the architecture declarative part. | - | DECL_SIGNAL |
| line 377 | then branch 376-378 in if 376-388 in process status_memory 374-389 in architecture 336-433; Target of a sequential signal assignment inside a process (assigned (others => '0')). | rstn_i = '0' | LHS_PROC |
| line 381 | then branch 380-381 in if 380-386 in elsif branch 379-387 in if 376-388 in process status_memory 374-389 in architecture 336-433; Target of a sequential signal assignment inside a process (assigned (others => '0')). | not (rstn_i = '0') AND rising_edge(clk_i) AND clr_i = '1' | LHS_PROC |
| line 383 | elsif branch 382-383 in if 380-386 in elsif branch 379-387 in if 376-388 in process status_memory 374-389 in architecture 336-433; Target indexed name of a sequential signal assignment inside a process; the array is indexed at to_integer(unsigned(acc_idx)). | not (rstn_i = '0') AND rising_edge(clk_i) AND not (clr_i = '1') AND inv_i = '1' | LHS_PROC, INDEXED_NAME |
| line 385 | elsif branch 384-385 in if 380-386 in elsif branch 379-387 in if 376-388 in process status_memory 374-389 in architecture 336-433; Target indexed name of a sequential signal assignment inside a process; the array is indexed at to_integer(unsigned(acc_idx)). | not (rstn_i = '0') AND rising_edge(clk_i) AND not (clr_i = '1') AND not (inv_i = '1') AND new_i = '1' | LHS_PROC, INDEXED_NAME |
| line 387 | elsif branch 379-387 in if 376-388 in process status_memory 374-389 in architecture 336-433; Prefix of an indexed name used as the right-hand side (valid_mem(to_integer(unsigned(acc_idx)))) of a sequential signal assignment; appears with an index. | not (rstn_i = '0') AND rising_edge(clk_i) | INDEXED_NAME |

### valid_mem_rd

from validate

| Occurrence Lines | Context | Path | SITE Tagged |
| --- | --- | --- | --- |
| line 345 | declarative part 339-360 in architecture 336-433; Declared signal in the architecture declarative part. | - | DECL_SIGNAL |
| line 378 | then branch 376-378 in if 376-388 in process status_memory 374-389 in architecture 336-433; Target of a sequential signal assignment inside a process (assigned '0'). | rstn_i = '0' | LHS_PROC |
| line 387 | elsif branch 379-387 in if 376-388 in process status_memory 374-389 in architecture 336-433; Target of a sequential signal assignment inside a process (assignment from indexed valid_mem). | not (rstn_i = '0') AND rising_edge(clk_i) | LHS_PROC |
| line 405 | when else 405-405 in architecture 336-433; Used inside the condition after when of a conditional signal assignment (when condition). | - | WHEN_COND |

### tag_mem

from validate

| Occurrence Lines | Context | Path | SITE Tagged |
| --- | --- | --- | --- |
| line 349 | declarative part 339-360 in architecture 336-433; Declared signal in the architecture declarative part. | - | DECL_SIGNAL |
| line 398 | then branch 397-398 in if 397-399 in then branch 396-400 in if 396-401 in process tag_memory 394-402 in architecture 336-433; Target indexed name of a sequential signal assignment inside a process; the array is indexed at to_integer(unsigned(acc_idx)). | rising_edge(clk_i) AND new_i = '1' | LHS_PROC, INDEXED_NAME |
| line 400 | then branch 396-400 in if 396-401 in process tag_memory 394-402 in architecture 336-433; Prefix of an indexed name used as the right-hand side (tag_mem(to_integer(unsigned(acc_idx)))) of a sequential signal assignment; appears with an index. | rising_edge(clk_i) | INDEXED_NAME |

### tag_mem_rd

from validate

| Occurrence Lines | Context | Path | SITE Tagged |
| --- | --- | --- | --- |
| line 350 | declarative part 339-360 in architecture 336-433; Declared signal in the architecture declarative part. | - | DECL_SIGNAL |
| line 400 | then branch 396-400 in if 396-401 in process tag_memory 394-402 in architecture 336-433; Target of a sequential signal assignment inside the tag_memory process (assigned from tag_mem(...)). | rising_edge(clk_i) | LHS_PROC |
| line 405 | when else 405-405 in architecture 336-433; Used inside the condition after when of a conditional signal assignment (compared to acc_tag). | - | WHEN_COND |

### data_mem_b0

from validate

| Occurrence Lines | Context | Path | SITE Tagged |
| --- | --- | --- | --- |
| line 354 | declarative part 339-360 in architecture 336-433; Declared signal (part of a multi-signal declaration) in the architecture declarative part. | - | DECL_SIGNAL |
| line 414 | then branch 413-414 in if 413-415 in then branch 412-428 in if 412-429 in process data_memory 410-430 in architecture 336-433; Target indexed name of a sequential signal assignment inside a process; the array is indexed at to_integer(unsigned(acc_adr)). | rising_edge(clk_i) AND we_i(0) = '1' | LHS_PROC, INDEXED_NAME |
| line 425 | then branch 412-428 in if 412-429 in process data_memory 410-430 in architecture 336-433; Prefix of an indexed name used as the right-hand side (data_mem_b0(to_integer(unsigned(acc_adr)))) of a sequential signal assignment; appears with an index. | rising_edge(clk_i) | INDEXED_NAME |

### data_mem_b1

from validate

| Occurrence Lines | Context | Path | SITE Tagged |
| --- | --- | --- | --- |
| line 354 | declarative part 339-360 in architecture 336-433; Declared signal (part of a multi-signal declaration) in the architecture declarative part. | - | DECL_SIGNAL |
| line 417 | then branch 416-417 in if 416-418 in then branch 412-428 in if 412-429 in process data_memory 410-430 in architecture 336-433; Target indexed name of a sequential signal assignment inside a process; the array is indexed at to_integer(unsigned(acc_adr)). | rising_edge(clk_i) AND we_i(1) = '1' | LHS_PROC, INDEXED_NAME |
| line 426 | then branch 412-428 in if 412-429 in process data_memory 410-430 in architecture 336-433; Prefix of an indexed name used as the right-hand side (data_mem_b1(to_integer(unsigned(acc_adr)))) of a sequential signal assignment; appears with an index. | rising_edge(clk_i) | INDEXED_NAME |

### data_mem_b2

from validate

| Occurrence Lines | Context | Path | SITE Tagged |
| --- | --- | --- | --- |
| line 354 | declarative part 339-360 in architecture 336-433; Declared signal (part of a multi-signal declaration) in the architecture declarative part. | - | DECL_SIGNAL |
| line 420 | then branch 419-420 in if 419-421 in then branch 412-428 in if 412-429 in process data_memory 410-430 in architecture 336-433; Target indexed name of a sequential signal assignment inside a process; the array is indexed at to_integer(unsigned(acc_adr)). | rising_edge(clk_i) AND we_i(2) = '1' | LHS_PROC, INDEXED_NAME |
| line 427 | then branch 412-428 in if 412-429 in process data_memory 410-430 in architecture 336-433; Prefix of an indexed name used as the right-hand side (data_mem_b2(to_integer(unsigned(acc_adr)))) of a sequential signal assignment; appears with an index. | rising_edge(clk_i) | INDEXED_NAME |

### data_mem_b3

from validate

| Occurrence Lines | Context | Path | SITE Tagged |
| --- | --- | --- | --- |
| line 354 | declarative part 339-360 in architecture 336-433; Declared signal (part of a multi-signal declaration) in the architecture declarative part. | - | DECL_SIGNAL |
| line 423 | then branch 422-423 in if 422-424 in then branch 412-428 in if 412-429 in process data_memory 410-430 in architecture 336-433; Target indexed name of a sequential signal assignment inside a process; the array is indexed at to_integer(unsigned(acc_adr)). | rising_edge(clk_i) AND we_i(3) = '1' | LHS_PROC, INDEXED_NAME |
| line 428 | then branch 412-428 in if 412-429 in process data_memory 410-430 in architecture 336-433; Prefix of an indexed name used as the right-hand side (data_mem_b3(to_integer(unsigned(acc_adr)))) of a sequential signal assignment; appears with an index. | rising_edge(clk_i) | INDEXED_NAME |

### acc_tag

from validate

| Occurrence Lines | Context | Path | SITE Tagged |
| --- | --- | --- | --- |
| line 357 | declarative part 339-360 in architecture 336-433; Declared signal in the architecture declarative part. | - | DECL_SIGNAL |
| line 366 | architecture 336-433; Target (left-hand side) of a concurrent signal assignment (assigned from addr_i part-select). | - | LHS_CONC |
| line 398 | then branch 397-398 in if 397-399 in then branch 396-400 in if 396-401 in process tag_memory 394-402 in architecture 336-433; Used as the whole right-hand side of a sequential signal assignment inside a process (assigned to tag_mem(...)). | rising_edge(clk_i) AND new_i = '1' | DIRR_ASS |
| line 405 | when else 405-405 in architecture 336-433; Used inside the condition after when of a conditional signal assignment (compared to tag_mem_rd). | - | WHEN_COND |

### acc_idx

from validate

| Occurrence Lines | Context | Path | SITE Tagged |
| --- | --- | --- | --- |
| line 358 | declarative part 339-360 in architecture 336-433; Declared signal in the architecture declarative part. | - | DECL_SIGNAL |
| line 367 | architecture 336-433; Target (left-hand side) of a concurrent signal assignment (assigned from addr_i part-select). | - | LHS_CONC |
| line 369 | architecture 336-433; Appears on the right-hand side of a concurrent signal assignment and is joined by the & operator (operand of the RHS expression). | - | RHS_OPERAND |
| line 383 | elsif branch 382-383 in if 380-386 in elsif branch 379-387 in if 376-388 in process status_memory 374-389 in architecture 336-433; Used inside the parentheses as the index expression (position) for valid_mem in a target indexed name; gives the array position. | not (rstn_i = '0') AND rising_edge(clk_i) AND not (clr_i = '1') AND inv_i = '1' | INDEX |
| line 385 | elsif branch 384-385 in if 380-386 in elsif branch 379-387 in if 376-388 in process status_memory 374-389 in architecture 336-433; Used inside the parentheses as the index expression (position) for valid_mem in a target indexed name; gives the array position. | not (rstn_i = '0') AND rising_edge(clk_i) AND not (clr_i = '1') AND not (inv_i = '1') AND new_i = '1' | INDEX |
| line 387 | elsif branch 379-387 in if 376-388 in process status_memory 374-389 in architecture 336-433; Used inside the parentheses as the index expression (position) for valid_mem in the right-hand side; gives the array position. | not (rstn_i = '0') AND rising_edge(clk_i) | INDEX |
| line 398 | then branch 397-398 in if 397-399 in then branch 396-400 in if 396-401 in process tag_memory 394-402 in architecture 336-433; Used inside the parentheses as the index expression (position) for tag_mem in a target indexed name; gives the array position. | rising_edge(clk_i) AND new_i = '1' | INDEX |
| line 400 | then branch 396-400 in if 396-401 in process tag_memory 394-402 in architecture 336-433; Used inside the parentheses as the index expression (position) for tag_mem in the right-hand side; gives the array position. | rising_edge(clk_i) | INDEX |

### acc_off

from validate

| Occurrence Lines | Context | Path | SITE Tagged |
| --- | --- | --- | --- |
| line 359 | declarative part 339-360 in architecture 336-433; Declared signal in a signal declaration. | - | DECL_SIGNAL |
| line 368 | architecture 336-433; Target of a concurrent signal assignment (left of <=). | - | LHS_CONC |
| line 369 | architecture 336-433; Operand on the right-hand side of a concurrent signal assignment, concatenated with acc_idx. | - | RHS_OPERAND |

### acc_adr

from validate

| Occurrence Lines | Context | Path | SITE Tagged |
| --- | --- | --- | --- |
| line 360 | declarative part 339-360 in architecture 336-433; Declared signal in a signal declaration. | - | DECL_SIGNAL |
| line 369 | architecture 336-433; Target of a concurrent signal assignment (left of <=). | - | LHS_CONC |
| line 414 | then branch 413-414 in if 413-415 in then branch 412-428 in if 412-429 in process data_memory 410-430 in architecture 336-433; Gives the array position used as the index of the target data_mem_b0(...) in a signal assignment. | rising_edge(clk_i) AND we_i(0) = '1' | INDEX |
| line 417 | then branch 416-417 in if 416-418 in then branch 412-428 in if 412-429 in process data_memory 410-430 in architecture 336-433; Gives the array position used as the index of the target data_mem_b1(...) in a signal assignment. | rising_edge(clk_i) AND we_i(1) = '1' | INDEX |
| line 420 | then branch 419-420 in if 419-421 in then branch 412-428 in if 412-429 in process data_memory 410-430 in architecture 336-433; Gives the array position used as the index of the target data_mem_b2(...) in a signal assignment. | rising_edge(clk_i) AND we_i(2) = '1' | INDEX |
| line 423 | then branch 422-423 in if 422-424 in then branch 412-428 in if 412-429 in process data_memory 410-430 in architecture 336-433; Gives the array position used as the index of the target data_mem_b3(...) in a signal assignment. | rising_edge(clk_i) AND we_i(3) = '1' | INDEX |
| line 425 | then branch 412-428 in if 412-429 in process data_memory 410-430 in architecture 336-433; Gives the array position used as the index inside the indexed RHS data_mem_b0(...) of a signal assignment. | rising_edge(clk_i) | INDEX |
| line 426 | then branch 412-428 in if 412-429 in process data_memory 410-430 in architecture 336-433; Gives the array position used as the index inside the indexed RHS data_mem_b1(...) of a signal assignment. | rising_edge(clk_i) | INDEX |
| line 427 | then branch 412-428 in if 412-429 in process data_memory 410-430 in architecture 336-433; Gives the array position used as the index inside the indexed RHS data_mem_b2(...) of a signal assignment. | rising_edge(clk_i) | INDEX |
| line 428 | then branch 412-428 in if 412-429 in process data_memory 410-430 in architecture 336-433; Gives the array position used as the index inside the indexed RHS data_mem_b3(...) of a signal assignment. | rising_edge(clk_i) | INDEX |
