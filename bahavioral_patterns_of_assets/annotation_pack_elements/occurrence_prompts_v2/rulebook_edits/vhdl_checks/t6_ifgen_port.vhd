library ieee; use ieee.std_logic_1164.all;
entity t6 is port (sel, d : in std_ulogic; q : out std_ulogic); end entity;
architecture a of t6 is
begin
  g: if sel = '1' generate
    q <= d;
  end generate;
end architecture;
