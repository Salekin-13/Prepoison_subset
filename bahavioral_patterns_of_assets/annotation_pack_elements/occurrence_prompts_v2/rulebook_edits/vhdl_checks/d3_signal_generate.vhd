library ieee; use ieee.std_logic_1164.all; use ieee.numeric_std.all;
entity d3 is generic (EN : boolean := true); port (a : in std_ulogic; q : out std_ulogic); end entity;
architecture x of d3 is begin
  g: if EN generate
    signal s_gen : std_ulogic;
  begin
    s_gen <= a; q <= s_gen;
  end generate g;
end architecture;
