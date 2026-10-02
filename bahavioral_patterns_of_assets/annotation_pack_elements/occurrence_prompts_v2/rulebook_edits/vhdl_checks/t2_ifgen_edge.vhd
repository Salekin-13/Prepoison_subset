library ieee; use ieee.std_logic_1164.all;
entity t2 is port (clk : in std_ulogic; d : in std_ulogic; q : out std_ulogic); end entity;
architecture a of t2 is
begin
  g_edge: if rising_edge(clk) generate
    q <= d;
  end generate;
end architecture;
