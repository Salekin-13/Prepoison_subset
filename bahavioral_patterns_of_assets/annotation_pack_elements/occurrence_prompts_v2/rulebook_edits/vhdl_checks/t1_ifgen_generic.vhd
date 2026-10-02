library ieee; use ieee.std_logic_1164.all;
entity t1 is generic (EN : boolean := true); port (clk : in std_ulogic; d : in std_ulogic; q : out std_ulogic); end entity;
architecture a of t1 is
begin
  g_on: if EN generate
    q <= d;
  end generate;
end architecture;
