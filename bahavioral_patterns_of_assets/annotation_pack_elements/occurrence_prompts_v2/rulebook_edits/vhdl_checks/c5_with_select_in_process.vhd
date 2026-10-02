library ieee; use ieee.std_logic_1164.all;
entity c5 is port (sel : in std_ulogic_vector(1 downto 0); a, b : in std_ulogic; q : out std_ulogic); end entity;
architecture x of c5 is begin
  p: process (sel, a, b) begin
    with sel select q <= a when "00", b when others;
  end process p;
end architecture;
