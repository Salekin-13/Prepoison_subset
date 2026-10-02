library ieee; use ieee.std_logic_1164.all;
entity c2 is port (sel, other : in std_ulogic_vector(1 downto 0); a, b : in std_ulogic; q : out std_ulogic); end entity;
architecture x of c2 is begin
  p: process (sel, other, a, b) begin
    case sel is
      when other => q <= a;
      when others => q <= b;
    end case;
  end process p;
end architecture;
